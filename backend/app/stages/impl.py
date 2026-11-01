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
from app.providers.search_provider import SearchProvider, SearchResult
from app.schemas.brief import ActivityType, Source
from app.services.activity_classifier import classify_activity, is_byline_match
from app.services.ai_brief_synthesizer import rule_based_synthesis, synthesize_with_ai
from app.services.brief_enrichment import enrich_brief
from app.services.career_analysis import analyse_career, build_career_timeline
from app.services.company_discovery import discover_company_domain, page_mentions_company
from app.services.identity_attribution import (
    augment_fingerprint_with_mentions,
    build_fingerprint,
    canonical_url,
    normalized_title,
    score_item,
)
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
        ctx.outputs.setdefault(
            "_profile_source",
            {
                "id": "profile",
                "url": (getattr(person, "linkedin_url", None) or "manual-entry")
                if person is not None
                else "manual-entry",
                "source_type": "social_profile",
            },
        )
        if person is None or not person.experiences:
            return StageResult(
                stage=self.name,
                output={
                    "total_months_experience": 0,
                    "note": "no structured experience data",
                    "career_timeline": [],
                },
            )
        insights = analyse_career(person.experiences)
        career_timeline = build_career_timeline(person.experiences, profile_source_id="profile")
        return StageResult(
            stage=self.name,
            output={
                "total_months_experience": insights.total_months_experience,
                "gaps_months": insights.gaps_months,
                "company_switches": insights.company_switches,
                "current_role_months": insights.current_role_months,
                "career_timeline": career_timeline,
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
        # Defense in depth against F5-class noise: even a domain that
        # passed the aggregator blocklist could turn out to be a
        # multi-company directory — drop any crawled page that doesn't
        # actually mention the company.
        relevant_pages = [p for p in pages if page_mentions_company(company, p.title, p.text)]
        website_sources = [
            {
                "url": p.url,
                "title": p.title,
                "excerpt": p.text[:280],
                "source_type": "company_website",
            }
            for p in relevant_pages
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
                "pages_crawled": len(relevant_pages),
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

        profile_source = ctx.outputs.get("_profile_source", {"id": "profile"})
        profile_source_id = profile_source.get("id", "profile")

        activity: list[dict] = []
        for post in posts:
            activity_type = classify_activity(post.text, is_known_repost=post.is_repost)
            if activity_type == ActivityType.OTHER_PUBLIC_ACTIVITY and not post.is_repost:
                activity_type = ActivityType.ORIGINAL_POST
            activity.append(
                {
                    "activity_type": activity_type.value,
                    "topic": post.text[:80],
                    "summary": post.text,
                    "url": post.url or "",
                    "published_at": post.posted_at,
                    "authored_by_person": not post.is_repost,
                    "relevance": None,
                    "confidence": "medium",
                    "source_ids": [profile_source_id],
                }
            )

        return StageResult(
            stage=self.name,
            output={
                "original_post_count": len(originals),
                "repost_count": len(reposts),
                "note": "no post history available" if not posts else None,
                "activity": activity,
            },
        )


class WebFootprintStage(Stage):
    name = StageName.WEB_FOOTPRINT

    def __init__(self, search: SearchProvider, known_other_employers: set[str] | None = None):
        self.search = search
        # Seeded by regression fixtures / future callers who already know of
        # a confirmed different person sharing this name and their employer
        # (e.g. from a prior disambiguation step). Empty by default — the
        # live pipeline has no such source yet for single-URL intake, so
        # items with no corroboration land in "unverified", not "namesake".
        self.known_other_employers = known_other_employers or set()

    async def run(self, ctx: StageContext) -> StageResult:
        person = ctx.outputs.get("_person")
        name = getattr(person, "full_name", None) or ""

        fp = build_fingerprint(
            full_name=name,
            linkedin_url=getattr(person, "linkedin_url", None) if person else None,
            current_company=getattr(person, "current_company", None) if person else None,
            headline=getattr(person, "headline", None) if person else None,
            experiences=getattr(person, "experiences", []) if person else [],
            education=getattr(person, "education", []) if person else [],
        )
        fp.known_other_employers = self.known_other_employers

        queries = [
            f'"{name}" interview OR podcast',
            f'"{name}" article OR publication',
            f'"{name}" talk OR conference OR webinar',
        ]

        seen_canonical: set[str] = set()
        merged: list[SearchResult] = []
        for query in queries:
            results = await self.search.search(query, max_results=10)
            for r in results:
                key = canonical_url(r.url)
                if key in seen_canonical:
                    continue
                seen_canonical.add(key)
                merged.append(r)

        # Bootstrap the fingerprint's schools from the run's own results
        # before scoring, so a thin/stale profile snapshot with no
        # education data doesn't cause a fresh, high-signal source (one
        # that names the subject and their school) to be scored against an
        # incomplete fingerprint.
        augment_fingerprint_with_mentions(
            fp, [f"{r.title or ''} {r.snippet or ''}" for r in merged]
        )

        sources: list[dict] = []
        activity: list[dict] = []
        # Namesake hits are not discarded outright — they're exactly the
        # evidence the "People with the Same Name" section needs, kept
        # separate from the target's own facts. Unverified hits (mentions
        # the name, no corroboration, no conflict) are excluded from the
        # brief entirely — absence of evidence isn't evidence either way.
        same_name_candidates: list[dict] = []
        unverified_count = 0
        seen_titles: set[str] = set()
        for r in merged:
            text = f"{r.title or ''} {r.snippet or ''}"
            title_key = normalized_title(r.title)
            if title_key and title_key in seen_titles:
                continue

            verdict, _hits = score_item(text, fp)
            if verdict == "drop":
                continue
            if verdict == "unverified":
                unverified_count += 1
                continue

            activity_type = classify_activity(text)
            authored_by_person = False
            if activity_type in (
                ActivityType.ARTICLE_OR_PUBLICATION,
                ActivityType.INTERVIEW_OR_PODCAST,
            ) and is_byline_match(name, text):
                authored_by_person = True

            if verdict == "namesake":
                same_name_candidates.append(
                    {
                        "name": name,
                        "identity_summary": r.title or r.url,
                        "distinguishing_info": r.snippet,
                        "url": r.url,
                        "why_confusable": f'Shares the full name "{name}" and surfaced in a public search for it.',
                        "why_different": "Mentions an employer already confirmed to belong to a "
                        f"different person named {name}, not to this person.",
                    }
                )
                if title_key:
                    seen_titles.add(title_key)
                continue

            # verdict == "subject"
            if title_key:
                seen_titles.add(title_key)
            sources.append({"url": r.url, "title": r.title, "excerpt": r.snippet})
            activity.append(
                {
                    "activity_type": activity_type.value,
                    "topic": (r.title or "")[:80],
                    "summary": r.snippet or "",
                    "url": r.url,
                    "published_at": None,
                    "authored_by_person": authored_by_person,
                    "relevance": None,
                    "confidence": "medium" if authored_by_person else "low",
                    "source_ids": [],
                }
            )

        gaps: list[str] = []
        if same_name_candidates:
            gaps.append(
                f"Found {len(same_name_candidates)} public mention(s) of a different person named "
                f'"{name}" (conflicting employer); listed separately under People with the Same '
                "Name rather than attributed to this person's activity."
            )
        if unverified_count:
            gaps.append(
                f"Found {unverified_count} public mention(s) of \"{name}\" that could not be "
                "confirmed as this person or as a different one (no corroborating or conflicting "
                "detail); excluded from the brief rather than guessed into either bucket."
            )

        return StageResult(
            stage=self.name,
            output={
                "footprint_items": len(merged),
                "activity": activity,
                "gaps": gaps,
                "same_name_candidates": same_name_candidates,
            },
            sources=sources,
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

        # profile_source goes first so it wins dedup below if the person's
        # own profile URL also surfaces as a web-footprint search hit
        # (audit F5: [profile] and a search-channel copy of the same URL
        # were previously counted as two separate sources).
        sources_raw: list[dict] = []
        profile_source = ctx.outputs.get("_profile_source")
        if profile_source is not None:
            sources_raw.append(profile_source)
        for stage_name in (
            StageName.RESEARCH_COMPANY.value,
            StageName.WEB_FOOTPRINT.value,
            StageName.ANALYSE_ACTIVITY.value,
        ):
            sources_raw.extend(ctx.outputs.get(f"_sources_{stage_name}", []))

        seen_source_urls: set[str] = set()
        deduped_raw: list[dict] = []
        for s in sources_raw:
            url = s.get("url")
            if not url:
                continue
            key = canonical_url(url)
            if key in seen_source_urls:
                continue
            seen_source_urls.add(key)
            deduped_raw.append(s)

        sources = [
            Source(
                id=s.get("id") or f"s{i}",
                url=s["url"],
                title=s.get("title"),
                excerpt=s.get("excerpt"),
                source_type=s.get("source_type", "other"),
                publisher=s.get("publisher"),
                published_at=s.get("published_at"),
            )
            for i, s in enumerate(deduped_raw)
        ]

        career = ctx.outputs.get(StageName.ANALYSE_CAREER.value, {})

        # Merge classified activity from both ANALYSE_ACTIVITY (profile posts)
        # and WEB_FOOTPRINT (search-discovered activity) — both stages
        # produce real classified activity items, dedupe by URL so overlap
        # between the two doesn't double-count.
        activity_from_posts = ctx.outputs.get(StageName.ANALYSE_ACTIVITY.value, {}).get(
            "activity", []
        )
        activity_from_footprint = ctx.outputs.get(StageName.WEB_FOOTPRINT.value, {}).get(
            "activity", []
        )
        activity: list[dict] = []
        seen_activity_urls: set[str] = set()
        for item in [*activity_from_posts, *activity_from_footprint]:
            url = item.get("url")
            if url and url in seen_activity_urls:
                continue
            if url:
                seen_activity_urls.add(url)
            activity.append(item)

        company_gaps = list(ctx.outputs.get(StageName.RESEARCH_COMPANY.value, {}).get("gaps", []))
        company_gaps.extend(ctx.outputs.get(StageName.WEB_FOOTPRINT.value, {}).get("gaps", []))
        for failed_stage, error in ctx.stage_failures.items():
            company_gaps.append(f"{failed_stage.value.replace('_', ' ')} failed: {error}")

        brief = None
        metadata = None
        if self.ai_provider is not None:
            try:
                brief, metadata = await synthesize_with_ai(
                    self.ai_provider, person_data or {}, career, activity, sources, company_gaps
                )
            except Exception as exc:  # noqa: BLE001 - any AI failure falls back honestly
                logger.warning("AI synthesis failed, falling back to rule-based: %s", exc)
                brief, metadata = None, None

        if brief is None:
            brief, metadata = rule_based_synthesis(
                person_data, career, activity, sources, company_gaps
            )
        elif company_gaps:
            # Safety net: even on the AI path, make sure company-research
            # gaps survive verbatim, in case the model dropped them.
            for gap in company_gaps:
                if gap not in brief.research_gaps.missing_information:
                    brief.research_gaps.missing_information.append(gap)

        brief = enrich_brief(
            brief,
            person_data=person_data,
            linkedin_url=(person_data or {}).get("linkedin_url"),
            education_records=(person_data or {}).get("education", []),
            profile_source_id=profile_source.get("id") if profile_source else None,
            company_research=ctx.outputs.get(StageName.RESEARCH_COMPANY.value),
            same_name_candidates=ctx.outputs.get(StageName.WEB_FOOTPRINT.value, {}).get(
                "same_name_candidates", []
            ),
            activity=activity,
        )

        output = brief.model_dump()
        output["_synthesis_metadata"] = metadata
        return StageResult(stage=self.name, output=output)
