"""Chanakya API: Agent 01 (Catalogue) + monthly run lifecycle.

Later agents (Company Scout, People Finder, ...) add their own routes in
their own phases; this router only covers what Phase 1/2 own: creating a
monthly run and submitting/reviewing its offering+ICP brief.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import AuthenticatedUser, get_current_user
from app.db.chanakya_models import MonthlyRun
from app.db.chanakya_repository import ChanakyaRunRepository
from app.db.session import get_session
from app.schemas.catalogue import MonthlyRunCreate, OfferingBriefInput
from app.schemas.chanakya import AgentName

router = APIRouter(prefix="/chanakya")


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
