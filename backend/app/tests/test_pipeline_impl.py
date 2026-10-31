import pytest

from app.providers.company_crawler import NullCrawler
from app.providers.profile_provider import ManualProvider
from app.providers.search_provider import NullSearchProvider
from app.schemas.profile import Experience, Person
from app.stages.base import StageContext, StageName
from app.stages.impl import (
    AnalyseActivityStage,
    AnalyseCareerStage,
    FetchProfileStage,
    ResearchCompanyStage,
    ResolveIdentityStage,
    SynthesiseBriefStage,
    WebFootprintStage,
)
from app.stages.pipeline import Pipeline


@pytest.mark.asyncio
async def test_analyse_career_stage_produces_career_timeline_and_profile_source():
    person = Person(
        full_name="Jane Doe",
        linkedin_url="https://linkedin.com/in/janedoe",
        experiences=[
            Experience(title="Eng", company="A", start_date="2018-01", end_date="2019-01"),
            Experience(title="Sr Eng", company="B", start_date="2019-06", end_date=None),
        ],
        source="manual",
    )
    ctx = StageContext(run_id="r1", depth="standard")
    ctx.outputs["_person"] = person

    result = await AnalyseCareerStage().run(ctx)

    assert len(result.output["career_timeline"]) == 2
    assert result.output["career_timeline"][0]["organization"] == "A"
    assert result.output["career_timeline"][0]["source_ids"] == ["profile"]
    assert ctx.outputs["_profile_source"] == {
        "id": "profile",
        "url": "https://linkedin.com/in/janedoe",
        "source_type": "social_profile",
    }


@pytest.mark.asyncio
async def test_full_pipeline_runs_end_to_end_in_manual_mode_without_any_credentials():
    stages = {
        StageName.RESOLVE_IDENTITY: ResolveIdentityStage(
            full_name="Jane Doe", linkedin_url=None, company=None
        ),
        StageName.FETCH_PROFILE: FetchProfileStage(
            ManualProvider(),
            linkedin_url=None,
            pasted_text="Jane Doe\nSenior Engineer at Acme\nBuilds reliable systems.",
        ),
        StageName.ANALYSE_CAREER: AnalyseCareerStage(),
        StageName.RESEARCH_COMPANY: ResearchCompanyStage(NullCrawler(), search=NullSearchProvider()),
        StageName.ANALYSE_ACTIVITY: AnalyseActivityStage(),
        StageName.WEB_FOOTPRINT: WebFootprintStage(NullSearchProvider()),
        StageName.SYNTHESISE_BRIEF: SynthesiseBriefStage(),
    }
    pipeline = Pipeline(stages)
    ctx = StageContext(run_id="integration-run", depth="standard")

    results = await pipeline.run(ctx)

    brief = results[StageName.SYNTHESISE_BRIEF].output
    assert brief["prospect_name"] == "Jane Doe"
    assert len(brief["snapshot"]) == 1
    # No search/crawler => no web sources => no hooks fabricated.
    assert brief["sources"] == []
    assert brief["hooks"] == []
    # No AI provider was passed to SynthesiseBriefStage => must be honest
    # that rule-based synthesis ran, never claim AI synthesis happened.
    assert brief["_synthesis_metadata"]["synthesis_method"] == "rule_based"


@pytest.mark.asyncio
async def test_full_pipeline_uses_ai_synthesis_when_provider_configured():
    import json

    from app.providers.ai_provider import Completion, Usage

    class FakeAiProvider:
        name = "fake"

        async def complete(self, prompt, *, max_tokens=1024, timeout_seconds=30.0):
            return Completion(
                text=json.dumps(
                    {
                        "prospect_name": "Jane Doe",
                        "snapshot": [],
                        "career_story": [],
                        "current_role": [],
                        "company": [],
                        "content_and_interests": [],
                        "communication_style": [],
                        "likely_priorities": [],
                        "hooks": [],
                        "dos_and_donts": [],
                    }
                ),
                model="fake-model",
                provider="fake",
                usage=Usage(input_tokens=10, output_tokens=5, estimated_cost_usd=0.0001),
            )

        async def health_check(self) -> bool:
            return True

    stages = {
        StageName.RESOLVE_IDENTITY: ResolveIdentityStage(
            full_name="Jane Doe", linkedin_url=None, company=None
        ),
        StageName.FETCH_PROFILE: FetchProfileStage(
            ManualProvider(), linkedin_url=None, pasted_text="Jane Doe\nEngineer at Acme"
        ),
        StageName.ANALYSE_CAREER: AnalyseCareerStage(),
        StageName.RESEARCH_COMPANY: ResearchCompanyStage(NullCrawler(), search=NullSearchProvider()),
        StageName.ANALYSE_ACTIVITY: AnalyseActivityStage(),
        StageName.WEB_FOOTPRINT: WebFootprintStage(NullSearchProvider()),
        StageName.SYNTHESISE_BRIEF: SynthesiseBriefStage(ai_provider=FakeAiProvider()),
    }
    pipeline = Pipeline(stages)
    ctx = StageContext(run_id="ai-run", depth="standard")

    results = await pipeline.run(ctx)
    brief = results[StageName.SYNTHESISE_BRIEF].output

    assert brief["_synthesis_metadata"]["synthesis_method"] == "ai"
    assert brief["_synthesis_metadata"]["provider"] == "fake"
    assert brief["_synthesis_metadata"]["estimated_cost_usd"] == 0.0001


class _FakeSearchProvider:
    name = "fake"

    def __init__(self, results):
        self._results = results

    async def search(self, query: str, max_results: int = 10):
        return self._results


class _QueryTrackingSearchProvider:
    """Returns different results depending on the query, and records every
    query it was called with so tests can assert on call shape/order."""

    name = "fake-tracking"

    def __init__(self, results_by_query_substring):
        self._results_by_query_substring = results_by_query_substring
        self.calls: list[tuple[str, int]] = []

    async def search(self, query: str, max_results: int = 10):
        self.calls.append((query, max_results))
        for substring, results in self._results_by_query_substring.items():
            if substring in query:
                return results
        return []


@pytest.mark.asyncio
async def test_research_company_stage_uses_discovered_domain_when_confident():
    from app.providers.search_provider import SearchResult
    from app.schemas.profile import Person

    search = _FakeSearchProvider(
        [
            SearchResult(
                url="https://acmerobotics.com/about",
                title="Acme Robotics - Official Website",
                snippet="Acme Robotics builds industrial robots.",
            )
        ]
    )
    stage = ResearchCompanyStage(NullCrawler(), search=search)
    ctx = StageContext(run_id="r1", depth="standard")
    ctx.outputs["_person"] = Person(
        full_name="Jane Doe", current_company="Acme Robotics", source="manual"
    )

    result = await stage.run(ctx)

    assert result.output["domain_guess"] == "acmerobotics.com"


@pytest.mark.asyncio
async def test_research_company_stage_reports_gap_when_no_confident_match():
    from app.schemas.profile import Person

    search = _FakeSearchProvider([])
    stage = ResearchCompanyStage(NullCrawler(), search=search)
    ctx = StageContext(run_id="r2", depth="standard")
    ctx.outputs["_person"] = Person(
        full_name="Jane Doe", current_company="Acme Robotics", source="manual"
    )

    result = await stage.run(ctx)

    assert result.output["domain_guess"] is None
    assert result.output["pages_crawled"] == 0
    assert result.sources == []
    assert result.output["gaps"] == [
        "Could not confidently identify Acme Robotics's official website"
    ]


@pytest.mark.asyncio
async def test_research_company_stage_searches_for_news_and_tags_source_types():
    from app.providers.company_crawler import CrawledPage
    from app.providers.search_provider import SearchResult
    from app.schemas.profile import Person

    class _FakeCrawler:
        name = "fake"

        async def crawl(self, domain: str, max_pages: int = 15):
            return [CrawledPage(url=f"https://{domain}/about", title="About", text="Acme Robotics builds robots.")]

    domain_result = SearchResult(
        url="https://acmerobotics.com/about",
        title="Acme Robotics - Official Website",
        snippet="Acme Robotics builds industrial robots.",
    )
    news_result = SearchResult(
        url="https://techcrunch.com/acme-robotics-raises-series-b",
        title="Acme Robotics raises Series B",
        snippet="Acme Robotics announced a new partnership and product launch.",
    )
    search = _QueryTrackingSearchProvider(
        {
            "official website": [domain_result],
            "announcement OR launch OR partnership": [news_result],
        }
    )

    stage = ResearchCompanyStage(_FakeCrawler(), search=search)
    ctx = StageContext(run_id="r3", depth="standard")
    ctx.outputs["_person"] = Person(
        full_name="Jane Doe", current_company="Acme Robotics", source="manual"
    )

    result = await stage.run(ctx)

    news_queries = [q for q, _ in search.calls if "announcement OR launch OR partnership" in q]
    assert news_queries == ['"Acme Robotics" announcement OR launch OR partnership']
    assert [max_results for q, max_results in search.calls if q == news_queries[0]] == [5]

    assert result.output["recent_news_count"] == 1

    website_sources = [s for s in result.sources if s["source_type"] == "company_website"]
    news_sources = [s for s in result.sources if s["source_type"] == "company_news"]
    assert len(website_sources) == 1
    assert website_sources[0]["url"] == "https://acmerobotics.com/about"
    assert len(news_sources) == 1
    assert news_sources[0]["url"] == "https://techcrunch.com/acme-robotics-raises-series-b"
