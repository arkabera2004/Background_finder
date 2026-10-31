from datetime import datetime, timezone

from app.core.config import settings
from app.db.memory_store import Run, RunStep, run_store
from app.providers.ai_selector import build_ai_provider
from app.providers.company_crawler import build_company_crawler
from app.providers.selector import ChainedProfileProvider
from app.providers.search_provider import build_search_provider
from app.services.identity_resolution import find_identity_candidates
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
from app.stages.pipeline import Pipeline, StageFailedError


class RunCancelledError(Exception):
    pass


def create_run(
    owner_id: str,
    depth: str,
    full_name: str,
    linkedin_url: str | None,
    company: str | None,
    pasted_text: str | None,
) -> Run:
    run = run_store.create(owner_id=owner_id, depth=depth)
    for stage in StageName:
        run.steps[stage.value] = RunStep(stage=stage.value)
    run.full_name = full_name
    run.linkedin_url = linkedin_url
    run.company = company
    run.pasted_text = pasted_text
    return run


async def check_identity_ambiguity(run: Run) -> bool:
    """For name+company intake with no direct URL/pasted text, search for
    candidate LinkedIn profiles. If more than one plausible match exists,
    pause the run for explicit user selection rather than guessing.
    Returns True if the run was paused (status set to
    needs_identity_selection), False if it's safe to proceed automatically
    (0 or 1 candidate)."""
    if run.linkedin_url or run.pasted_text or not run.company:
        return False

    search = build_search_provider(
        settings.search_provider, settings.tavily_api_key or None, settings.searxng_base_url or None
    )
    candidates = await find_identity_candidates(run.full_name, run.company, search)

    if len(candidates) <= 1:
        if candidates:
            run.linkedin_url = candidates[0].linkedin_url
        return False

    run.status = "needs_identity_selection"
    run.identity_candidates = [
        {"linkedin_url": c.linkedin_url, "title": c.title, "snippet": c.snippet} for c in candidates
    ]
    return True


def select_identity(run: Run, linkedin_url: str) -> None:
    """Explicit user selection among ambiguous candidates. Persists the
    choice and un-pauses the run."""
    run.linkedin_url = linkedin_url
    run.identity_candidates = []
    run.status = "pending"


async def execute_run(run: Run) -> None:
    run.status = "running"

    def on_event(stage: StageName, event: str) -> None:
        step = run.steps[stage.value]
        now = datetime.now(timezone.utc)
        if run.cancel_requested:
            raise RunCancelledError()
        if event == "started":
            step.status = "running"
            step.started_at = now
        elif event == "completed":
            step.status = "completed"
            step.completed_at = now
        elif event == "failed":
            step.status = "failed"
            step.completed_at = now

    stages = {
        StageName.RESOLVE_IDENTITY: ResolveIdentityStage(
            full_name=run.full_name,
            linkedin_url=run.linkedin_url,
            company=run.company,
        ),
        StageName.FETCH_PROFILE: FetchProfileStage(
            ChainedProfileProvider(settings.bright_data_api_key or None, settings.pdl_api_key or None),
            linkedin_url=run.linkedin_url,
            pasted_text=run.pasted_text,
            full_name=run.full_name or None,
        ),
        StageName.ANALYSE_CAREER: AnalyseCareerStage(),
        StageName.RESEARCH_COMPANY: ResearchCompanyStage(
            build_company_crawler(settings.extraction_provider, settings.firecrawl_api_key or None)
        ),
        StageName.ANALYSE_ACTIVITY: AnalyseActivityStage(),
        StageName.WEB_FOOTPRINT: WebFootprintStage(
            build_search_provider(
                settings.search_provider, settings.tavily_api_key or None, settings.searxng_base_url or None
            )
        ),
        StageName.SYNTHESISE_BRIEF: SynthesiseBriefStage(ai_provider=build_ai_provider(settings)),
    }
    pipeline = Pipeline(stages)
    ctx = StageContext(run_id=run.id, depth=run.depth)

    try:
        results = await pipeline.run(ctx, on_event=on_event)
    except RunCancelledError:
        run.status = "cancelled"
        return
    except StageFailedError as exc:
        run.status = "failed"
        run.steps[exc.stage.value].error = str(exc.cause)
        return

    run.brief = results[StageName.SYNTHESISE_BRIEF].output
    run.status = "completed"
    run.completed_at = datetime.now(timezone.utc)
