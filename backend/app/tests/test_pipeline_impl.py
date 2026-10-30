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
        StageName.RESEARCH_COMPANY: ResearchCompanyStage(NullCrawler()),
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
