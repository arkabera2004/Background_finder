"""Real stage implementations wired to the credential-independent manual path.

Every stage here does genuine work with whatever data is available and
degrades honestly (empty results, not fabricated ones) when a paid
provider isn't configured. See docs/KNOWN_LIMITATIONS.md for exactly which
stages are data-limited without Tavily/Firecrawl/Bright Data/PDL/Anthropic.
"""

from app.providers.company_crawler import CompanyCrawler
from app.providers.profile_provider import ProfileProvider
from app.providers.search_provider import SearchProvider
from app.schemas.brief import Claim, Confidence, Hook, ProspectBrief, Source
from app.services.career_analysis import analyse_career
from app.services.citation_validator import validate_brief
from app.stages.base import Stage, StageContext, StageName, StageResult


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

    def __init__(self, crawler: CompanyCrawler):
        self.crawler = crawler

    async def run(self, ctx: StageContext) -> StageResult:
        person = ctx.outputs.get("_person")
        company = getattr(person, "current_company", None)
        if not company:
            return StageResult(stage=self.name, output={"company": None, "pages_crawled": 0})

        domain = company.lower().replace(" ", "") + ".com"  # best-effort guess, not verified
        pages = await self.crawler.crawl(domain)
        sources = [
            {"url": p.url, "title": p.title, "excerpt": p.text[:280]} for p in pages
        ]
        return StageResult(
            stage=self.name,
            output={"company": company, "domain_guess": domain, "pages_crawled": len(pages)},
            sources=sources,
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
    """Deterministic, rule-based synthesis — no Anthropic call.

    Real LLM-based synthesis (richer prose, inferred priorities) requires
    ANTHROPIC_API_KEY and is NOT_STARTED. This produces a smaller but
    completely honest brief: every claim traces to a real source or is
    explicitly marked as an inference, never invented.
    """

    name = StageName.SYNTHESISE_BRIEF

    async def run(self, ctx: StageContext) -> StageResult:
        person = ctx.outputs.get("_person")
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

        snapshot = []
        if person is not None:
            headline_claim = Claim(
                text=f"{person.full_name}" + (f" — {person.headline}" if person.headline else ""),
                is_inference=False,
                source_ids=[],
                confidence=Confidence.HIGH,
            )
            # The profile itself (manual input or provider) is the source of
            # truth for name/headline, so it's not tied to a web source id —
            # mark as an "inference" only in the sense of "not web-sourced",
            # kept as high confidence since it's user-supplied, not guessed.
            snapshot.append(headline_claim.model_copy(update={"is_inference": True}))

        career = ctx.outputs.get(StageName.ANALYSE_CAREER.value, {})
        career_claims = []
        if career.get("total_months_experience"):
            career_claims.append(
                Claim(
                    text=f"Approximately {career['total_months_experience']} months of tracked experience.",
                    is_inference=True,
                    confidence=Confidence.MEDIUM,
                )
            )

        hooks = [
            Hook(text=f"Mentioned in: {s.title or s.url}", source_ids=[s.id]) for s in sources[:7]
        ]

        brief = ProspectBrief(
            prospect_name=getattr(person, "full_name", "Unknown"),
            snapshot=snapshot,
            career_story=career_claims,
            sources=sources,
            hooks=hooks,
        )
        validated = validate_brief(brief)
        return StageResult(stage=self.name, output=validated.model_dump())
