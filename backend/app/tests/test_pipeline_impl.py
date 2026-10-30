import pytest

from app.providers.company_crawler import NullCrawler
from app.providers.profile_provider import ManualProvider
from app.providers.search_provider import NullSearchProvider
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
        StageName.RESEARCH_COMPANY: ResearchCompanyStage(NullCrawler()),
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
