"""Agent 01 — Catalogue: monthly run lifecycle + offering/ICP intake."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.api.routers.chanakya.shared import get_run_or_404, run_to_dict, snapshot_to_dict
from app.core.auth import AuthenticatedUser, get_current_user
from app.core.config import settings
from app.db.chanakya_repository import ChanakyaRunRepository
from app.db.session import get_session
from app.schemas.catalogue import MonthlyRunCreate, OfferingBriefInput
from app.schemas.chanakya import AgentName

router = APIRouter(prefix="/chanakya")


@router.post("/runs", status_code=201)
async def create_run(
    payload: MonthlyRunCreate, user: AuthenticatedUser = Depends(get_current_user)
) -> dict:
    session = get_session()
    try:
        repo = ChanakyaRunRepository(session)
        since = datetime.now(timezone.utc) - timedelta(days=1)
        if repo.count_recent_runs_for_owner(user.user_id, since) >= settings.max_chanakya_runs_per_user_per_day:
            raise HTTPException(
                status_code=429,
                detail=f"Daily limit of {settings.max_chanakya_runs_per_user_per_day} Chanakya runs exceeded",
            )
        run = repo.create_run(user.user_id, payload.period, payload.config)
        return run_to_dict(run)
    finally:
        session.close()


@router.get("/runs")
async def list_runs(user: AuthenticatedUser = Depends(get_current_user)) -> list[dict]:
    session = get_session()
    try:
        repo = ChanakyaRunRepository(session)
        return [run_to_dict(r) for r in repo.list_for_owner(user.user_id)]
    finally:
        session.close()


@router.get("/runs/{run_id}")
async def get_run(run_id: str, user: AuthenticatedUser = Depends(get_current_user)) -> dict:
    session = get_session()
    try:
        repo = ChanakyaRunRepository(session)
        return run_to_dict(get_run_or_404(repo, run_id, user.user_id))
    finally:
        session.close()


@router.post("/runs/{run_id}/offerings", status_code=201)
async def submit_offering_brief(
    run_id: str, payload: OfferingBriefInput, user: AuthenticatedUser = Depends(get_current_user)
) -> dict:
    """Submit or revise the monthly offering + ICP brief.

    Each call creates a new version (manual review/editing never overwrites
    a prior snapshot), and marks the Catalogue agent complete so the run is
    ready for Agent 02 (Company Scout).
    """
    session = get_session()
    try:
        repo = ChanakyaRunRepository(session)
        run = get_run_or_404(repo, run_id, user.user_id)

        repo.start_agent(run_id, AgentName.CATALOGUE)
        snapshot = repo.add_offering_snapshot(
            run, {"offerings": [o.model_dump() for o in payload.offerings], "filters": payload.filters}
        )
        repo.complete_agent(
            run_id, AgentName.CATALOGUE, {"offering_count": len(payload.offerings), "version": snapshot.version}
        )
        return snapshot_to_dict(snapshot)
    finally:
        session.close()


@router.get("/runs/{run_id}/offerings")
async def list_offering_snapshots(
    run_id: str, user: AuthenticatedUser = Depends(get_current_user)
) -> list[dict]:
    session = get_session()
    try:
        repo = ChanakyaRunRepository(session)
        run = get_run_or_404(repo, run_id, user.user_id)
        return [snapshot_to_dict(s) for s in sorted(run.offering_snapshots, key=lambda s: s.version)]
    finally:
        session.close()
