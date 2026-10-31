"""Real stage implementations wired to the credential-independent manual path.

Every stage here does genuine work with whatever data is available and
degrades honestly (empty results, not fabricated ones) when a paid
provider isn't configured. See docs/KNOWN_LIMITATIONS.md for exactly which
stages are data-limited without Tavily/Firecrawl/Bright Data/PDL/Anthropic.
"""

import logging

from app.providers.ai_provider import AiProvider
from app.providers.company_crawler import CompanyCrawler
from app.providers.profile_provider import ProfileProvider
from app.providers.search_provider import SearchProvider
from app.schemas.brief import Source
from app.services.ai_brief_synthesizer import rule_based_synthesis, synthesize_with_ai
from app.services.career_analysis import analyse_career
from app.services.company_discovery import discover_company_domain
from app.stages.base import Stage, StageContext, StageName, StageResult

logger = logging.getLogger(__name__)


class ResolveIdentityStage(Stage):
    """No search provider configured => trust the user-submitted identity
    directly rather than fabricating candidate matching. Real identity
    disambiguation (multiple candidates, match scoring) requires a search
    provider — NOT_STARTED, tracked in docs/KNOWN_LIMITATIONS.md."""

    name = StageName.RESOLVE_IDENTITY

    def __init__(self, full_name: str, linkedin_url: str | None, company: str | None):
        self.full_name = full_name
        self.linkedin_url = linkedin_url
        self.company = company

    async def run(self, ctx: StageContext) -> StageResult:
        return StageResult(
            stage=self.name,
            output={
                "resolved_name": self.full_name,
                "linkedin_url": self.linkedin_url,
                "company": self.company,
                "method": "user_supplied",
            },
        )


class FetchProfileStage(Stage):
    name = StageName.FETCH_PROFILE

    def __init__(
        self,
        provider: ProfileProvider,
        linkedin_url: str | None,
        pasted_text: str | None,
        full_name: str | None = None,
    ):
        self.provider = provider
        self.linkedin_url = linkedin_url
        self.pasted_text = pasted_text
        self.full_name = full_name

    async def run(self, ctx: StageContext) -> StageResult:
        person = await self.provider.fetch_profile(
            self.linkedin_url, self.pasted_text, self.full_name
        )
        ctx.outputs["_person"] = person
        return StageResult(stage=self.name, output=person.model_dump())


class AnalyseCareerStage(Stage):
    name = StageName.ANALYSE_CAREER

    async def run(self, ctx: StageContext) -> StageResult:
        person = ctx.outputs.get("_person")
        if person is None or not person.experiences:
            return StageResult(
                stage=self.name,
                output={"total_months_experience": 0, "note": "no structured experience data"},
            )
        insights = analyse_career(person.experiences)
        return StageResult(
            stage=self.name,
            output={
                "total_months_experience": insights.total_months_experience,
                "gaps_months": insights.gaps_months,
                "company_switches": insights.company_switches,
                "current_role_months": insights.current_role_months,
            },
        )


class ResearchCompanyStage(Stage):
    name = StageName.RESEARCH_COMPANY

    def __init__(self, crawler: CompanyCrawler, search: SearchProvider):
        self.crawler = crawler
        self.search = search

    async def run(self, ctx: StageContext) -> StageResult:
        person = ctx.outputs.get("_person")
        company = getattr(person, "current_company", None)
        if not company:
            return StageResult(stage=self.name, output={"company": None, "pages_crawled": 0})

        domain = await discover_company_domain(self.search, company)
        if domain is None:
            return StageResult(
                stage=self.name,
                output={
                    "company": company,
                    "domain_guess": None,
                    "pages_crawled": 0,
                    "gaps": [f"Could not confidently identify {company}'s official website"],
                },
                sources=[],
            )
        pages = await self.crawler.crawl(domain)
        website_sources = [
            {
                "url": p.url,
                "title": p.title,
                "excerpt": p.text[:280],
                "source_type": "company_website",
            }
            for p in pages
        ]

        news_results = await self.search.search(
            f'"{company}" announcement OR launch OR partnership', max_results=5
        )
        news_sources = [
            {
                "url": r.url,
                "title": r.title,
                "excerpt": r.snippet,
                "source_type": "company_news",
            }
            for r in news_results
        ]

        return StageResult(
            stage=self.name,
            output={
                "company": company,
                "domain_guess": domain,
                "pages_crawled": len(pages),
                "recent_news_count": len(news_results),
            },
            sources=website_sources + news_sources,
        )


class AnalyseActivityStage(Stage):
    name = StageName.ANALYSE_ACTIVITY

    async def run(self, ctx: StageContext) -> StageResult:
        person = ctx.outputs.get("_person")
        posts = getattr(person, "posts", []) if person else []
        originals = [p for p in posts if not p.is_repost]
        reposts = [p for p in posts if p.is_repost]
        return StageResult(
            stage=self.name,
            output={
                "original_post_count": len(originals),
                "repost_count": len(reposts),
                "note": "no post history available" if not posts else None,
            },
        )


class WebFootprintStage(Stage):
    name = StageName.WEB_FOOTPRINT

    def __init__(self, search: SearchProvider):
        self.search = search

    async def run(self, ctx: StageContext) -> StageResult:
        person = ctx.outputs.get("_person")
        name = getattr(person, "full_name", None) or ""
        results = await self.search.search(f'"{name}" interview OR podcast OR article', max_results=10)
        sources = [{"url": r.url, "title": r.title, "excerpt": r.snippet} for r in results]
        return StageResult(
            stage=self.name, output={"footprint_items": len(results)}, sources=sources
        )


class SynthesiseBriefStage(Stage):
    """Synthesises the Prospect Brief.

    Tries the configured AiProvider first (if one is given); on any
    failure — no provider configured, provider unreachable, invalid
    structured output twice — falls back to the original deterministic
    rule-based synthesis. The output always records which path was
    actually used (`_synthesis_metadata.synthesis_method`), so the app
    never claims AI synthesis happened when it didn't.
    """

    name = StageName.SYNTHESISE_BRIEF

    def __init__(self, ai_provider: AiProvider | None = None):
        self.ai_provider = ai_provider

    async def run(self, ctx: StageContext) -> StageResult:
        person = ctx.outputs.get("_person")
        person_data = person.model_dump() if person is not None else None

        sources_raw: list[dict] = []
        for stage_name in (
            StageName.RESEARCH_COMPANY.value,
            StageName.WEB_FOOTPRINT.value,
        ):
            sources_raw.extend(ctx.outputs.get(f"_sources_{stage_name}", []))

        sources = [
            Source(id=f"s{i}", url=s["url"], title=s.get("title"), excerpt=s.get("excerpt"))
            for i, s in enumerate(sources_raw)
            if s.get("url")
        ]

        career = ctx.outputs.get(StageName.ANALYSE_CAREER.value, {})

        brief = None
        metadata = None
        if self.ai_provider is not None:
            try:
                brief, metadata = await synthesize_with_ai(
                    self.ai_provider, person_data or {}, career, sources
                )
            except Exception as exc:  # noqa: BLE001 - any AI failure falls back honestly
                logger.warning("AI synthesis failed, falling back to rule-based: %s", exc)
                brief, metadata = None, None

        if brief is None:
            brief, metadata = rule_based_synthesis(person_data, career, sources)

        output = brief.model_dump()
        output["_synthesis_metadata"] = metadata
        return StageResult(stage=self.name, output=output)
