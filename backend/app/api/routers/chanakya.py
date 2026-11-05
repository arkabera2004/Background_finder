"""Chanakya API: Agent 01 (Catalogue) + monthly run lifecycle.

Later agents (Company Scout, People Finder, ...) add their own routes in
their own phases; this router only covers what Phase 1/2 own: creating a
monthly run and submitting/reviewing its offering+ICP brief.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import AuthenticatedUser, get_current_user
from app.core.config import settings
from app.db.chanakya_models import MonthlyRun, ScoutedCompany
from app.db.chanakya_repository import ChanakyaRunRepository
from app.db.session import get_session
from app.providers.search_provider import build_search_provider
from app.schemas.catalogue import MonthlyRunCreate, OfferingBriefInput
from app.schemas.chanakya import AgentName
from app.services.company_scout import discover_candidates

router = APIRouter(prefix="/chanakya")

DEFAULT_TARGET_COMPANY_COUNT = 100


def _run_to_dict(run: MonthlyRun) -> dict:
    return {
        "id": run.id,
        "period": run.period,
        "status": run.status,
        "config": run.config,
        "created_at": run.created_at.isoformat(),
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "agent_executions": [
            {
                "agent_name": e.agent_name,
                "status": e.status,
                "retry_count": e.retry_count,
                "error": e.error,
                "output_summary": e.output_summary,
            }
            for e in run.agent_executions
        ],
    }


def _snapshot_to_dict(snapshot) -> dict:
    return {
        "id": snapshot.id,
        "run_id": snapshot.run_id,
        "version": snapshot.version,
        "data": snapshot.data,
        "created_at": snapshot.created_at.isoformat(),
    }


def _company_to_dict(company: ScoutedCompany) -> dict:
    return {
        "id": company.id,
        "run_id": company.run_id,
        "name": company.name,
        "domain": company.domain,
        "fit_score": company.fit_score,
        "selected": company.selected,
        "source_url": company.source_url,
        "created_at": company.created_at.isoformat(),
    }


@router.post("/runs", status_code=201)
async def create_run(
    payload: MonthlyRunCreate, user: AuthenticatedUser = Depends(get_current_user)
) -> dict:
    session = get_session()
    try:
        repo = ChanakyaRunRepository(session)
        run = repo.create_run(user.user_id, payload.period, payload.config)
        return _run_to_dict(run)
    finally:
        session.close()


@router.get("/runs")
async def list_runs(user: AuthenticatedUser = Depends(get_current_user)) -> list[dict]:
    session = get_session()
    try:
        repo = ChanakyaRunRepository(session)
        return [_run_to_dict(r) for r in repo.list_for_owner(user.user_id)]
    finally:
        session.close()


@router.get("/runs/{run_id}")
async def get_run(run_id: str, user: AuthenticatedUser = Depends(get_current_user)) -> dict:
    session = get_session()
    try:
        repo = ChanakyaRunRepository(session)
        run = repo.get(run_id, owner_id=user.user_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        return _run_to_dict(run)
    finally:
        session.close()


@router.post("/runs/{run_id}/offerings", status_code=201)
async def submit_offering_brief(
    run_id: str, payload: OfferingBriefInput, user: AuthenticatedUser = Depends(get_current_user)
) -> dict:
    """Agent 01: submit or revise the monthly offering + ICP brief.

    Each call creates a new version (manual review/editing never overwrites
    a prior snapshot), and marks the Catalogue agent complete so the run is
    ready for Agent 02 (Company Scout) in a later phase.
    """
    session = get_session()
    try:
        repo = ChanakyaRunRepository(session)
        run = repo.get(run_id, owner_id=user.user_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")

        repo.start_agent(run_id, AgentName.CATALOGUE)
        snapshot = repo.add_offering_snapshot(
            run, {"offerings": [o.model_dump() for o in payload.offerings], "filters": payload.filters}
        )
        repo.complete_agent(
            run_id, AgentName.CATALOGUE, {"offering_count": len(payload.offerings), "version": snapshot.version}
        )
        return _snapshot_to_dict(snapshot)
    finally:
        session.close()


@router.get("/runs/{run_id}/offerings")
async def list_offering_snapshots(
    run_id: str, user: AuthenticatedUser = Depends(get_current_user)
) -> list[dict]:
    session = get_session()
    try:
        repo = ChanakyaRunRepository(session)
        run = repo.get(run_id, owner_id=user.user_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        return [_snapshot_to_dict(s) for s in sorted(run.offering_snapshots, key=lambda s: s.version)]
    finally:
        session.close()


@router.post("/runs/{run_id}/company-scout", status_code=200)
async def run_company_scout(run_id: str, user: AuthenticatedUser = Depends(get_current_user)) -> dict:
    """Agent 02: discover companies against the run's latest offering
    brief, score them for ICP fit, dedupe by domain, and select the
    configured (default 100) top companies. Requires a submitted offering
    brief first (Agent 01)."""
    session = get_session()
    try:
        repo = ChanakyaRunRepository(session)
        run = repo.get(run_id, owner_id=user.user_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        if not run.offering_snapshots:
            raise HTTPException(
                status_code=409, detail="Submit an offering brief (Agent 01) before running Company Scout"
            )
        latest = max(run.offering_snapshots, key=lambda s: s.version)

        repo.start_agent(run_id, AgentName.COMPANY_SCOUT)
        try:
            search = build_search_provider(
                settings.search_provider, settings.tavily_api_key or None, settings.searxng_base_url or None
            )
            candidates = await discover_candidates(
                search, latest.data.get("offerings", []), latest.data.get("filters", {})
            )
            repo.upsert_scouted_companies(run_id, user.user_id, candidates)
            target_count = run.config.get("target_company_count", DEFAULT_TARGET_COMPANY_COUNT)
            selected = repo.select_top_companies(run_id, target_count)
            for company in selected:
                repo.add_evidence(
                    run_id,
                    AgentName.COMPANY_SCOUT,
                    entity_type="company",
                    entity_id=company.id,
                    source_url=company.source_url,
                    confidence=company.fit_score,
                )
        except Exception as exc:  # noqa: BLE001 - record and re-raise as a clean 502
            repo.fail_agent(run_id, AgentName.COMPANY_SCOUT, str(exc))
            raise HTTPException(status_code=502, detail=f"Company Scout failed: {exc}") from exc

        repo.complete_agent(
            run_id,
            AgentName.COMPANY_SCOUT,
            {"candidates_found": len(candidates), "selected": len(selected)},
        )
        return {"candidates_found": len(candidates), "selected": [_company_to_dict(c) for c in selected]}
    finally:
        session.close()


@router.get("/runs/{run_id}/companies")
async def list_scouted_companies(
    run_id: str, selected_only: bool = False, user: AuthenticatedUser = Depends(get_current_user)
) -> list[dict]:
    session = get_session()
    try:
        repo = ChanakyaRunRepository(session)
        run = repo.get(run_id, owner_id=user.user_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        return [_company_to_dict(c) for c in repo.list_scouted_companies(run_id, selected_only)]
    finally:
        session.close()
