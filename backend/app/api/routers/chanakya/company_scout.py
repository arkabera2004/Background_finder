"""Agent 02 — Company Scout: discover, score, dedupe, select companies."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.routers.chanakya.shared import company_to_dict, get_run_or_404
from app.core.auth import AuthenticatedUser, get_current_user
from app.core.config import settings
from app.db.chanakya_repository import ChanakyaRunRepository
from app.db.session import get_session
from app.providers.search_provider import build_search_provider
from app.schemas.chanakya import AgentName
from app.services.company_scout import discover_candidates

router = APIRouter(prefix="/chanakya")

DEFAULT_TARGET_COMPANY_COUNT = 100


@router.post("/runs/{run_id}/company-scout", status_code=200)
async def run_company_scout(run_id: str, user: AuthenticatedUser = Depends(get_current_user)) -> dict:
    """Discover companies against the run's latest offering brief, score
    them for ICP fit, dedupe by domain, and select the configured
    (default 100) top companies. Requires a submitted offering brief
    first (Agent 01)."""
    session = get_session()
    try:
        repo = ChanakyaRunRepository(session)
        run = get_run_or_404(repo, run_id, user.user_id)
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
            repo.fail_agent(run_id, AgentName.COMPANY_SCOUT, f"{type(exc).__name__}: {exc}")
            raise HTTPException(status_code=502, detail=f"Company Scout failed: {exc}") from exc

        repo.complete_agent(
            run_id,
            AgentName.COMPANY_SCOUT,
            {"candidates_found": len(candidates), "selected": len(selected)},
        )
        return {"candidates_found": len(candidates), "selected": [company_to_dict(c) for c in selected]}
    finally:
        session.close()


@router.get("/runs/{run_id}/companies")
async def list_scouted_companies(
    run_id: str, selected_only: bool = False, user: AuthenticatedUser = Depends(get_current_user)
) -> list[dict]:
    session = get_session()
    try:
        repo = ChanakyaRunRepository(session)
        get_run_or_404(repo, run_id, user.user_id)
        return [company_to_dict(c) for c in repo.list_scouted_companies(run_id, selected_only)]
    finally:
        session.close()


@router.get("/companies")
async def list_all_companies(
    selected_only: bool = False, user: AuthenticatedUser = Depends(get_current_user)
) -> list[dict]:
    """Cross-run view: every company this owner's monthly runs have ever
    scouted, across all periods — the aggregate equivalent of the
    per-run endpoint above."""
    session = get_session()
    try:
        repo = ChanakyaRunRepository(session)
        return [
            company_to_dict(c)
            for c in repo.list_all_scouted_companies_for_owner(user.user_id, selected_only)
        ]
    finally:
        session.close()
