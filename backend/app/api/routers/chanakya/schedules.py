"""Phase 5 — durable monthly scheduler: tenant CRUD for recurring runs.

Creating/editing/disabling a schedule is a plain CRUD API; the actual
unattended triggering happens in `app/workers/main.py`'s daily ARQ cron
(`run_due_chanakya_schedules`), not here. A manual `/chanakya/runs` +
`/orchestrate` call always remains available regardless of schedules.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import AuthenticatedUser, get_current_user
from app.db.chanakya_models import ChanakyaSchedule
from app.db.chanakya_repository import ChanakyaRunRepository
from app.db.session import get_session
from app.schemas.schedule import ScheduleCreate, ScheduleUpdate

router = APIRouter(prefix="/chanakya")


def schedule_to_dict(schedule: ChanakyaSchedule) -> dict:
    return {
        "id": schedule.id,
        "enabled": schedule.enabled,
        "day_of_month": schedule.day_of_month,
        "offerings": schedule.offerings,
        "filters": schedule.filters,
        "config": schedule.config,
        "last_run_period": schedule.last_run_period,
        "last_run_id": schedule.last_run_id,
        "last_run_status": schedule.last_run_status,
        "last_run_error": schedule.last_run_error,
        "created_at": schedule.created_at.isoformat(),
    }


@router.post("/schedules", status_code=201)
async def create_schedule(
    payload: ScheduleCreate, user: AuthenticatedUser = Depends(get_current_user)
) -> dict:
    session = get_session()
    try:
        repo = ChanakyaRunRepository(session)
        schedule = repo.create_schedule(
            owner_id=user.user_id,
            offerings=[o.model_dump() for o in payload.offerings],
            filters=payload.filters,
            config=payload.config,
            day_of_month=payload.day_of_month,
            enabled=payload.enabled,
        )
        return schedule_to_dict(schedule)
    finally:
        session.close()


@router.get("/schedules")
async def list_schedules(user: AuthenticatedUser = Depends(get_current_user)) -> list[dict]:
    session = get_session()
    try:
        repo = ChanakyaRunRepository(session)
        return [schedule_to_dict(s) for s in repo.list_schedules_for_owner(user.user_id)]
    finally:
        session.close()


@router.patch("/schedules/{schedule_id}")
async def update_schedule(
    schedule_id: str, payload: ScheduleUpdate, user: AuthenticatedUser = Depends(get_current_user)
) -> dict:
    session = get_session()
    try:
        repo = ChanakyaRunRepository(session)
        schedule = repo.get_schedule(schedule_id, user.user_id)
        if schedule is None:
            raise HTTPException(status_code=404, detail="Schedule not found")
        if payload.enabled is not None:
            repo.set_schedule_enabled(schedule, payload.enabled)
        return schedule_to_dict(schedule)
    finally:
        session.close()


@router.delete("/schedules/{schedule_id}", status_code=204)
async def delete_schedule(schedule_id: str, user: AuthenticatedUser = Depends(get_current_user)) -> None:
    session = get_session()
    try:
        repo = ChanakyaRunRepository(session)
        schedule = repo.get_schedule(schedule_id, user.user_id)
        if schedule is None:
            raise HTTPException(status_code=404, detail="Schedule not found")
        repo.delete_schedule(schedule)
    finally:
        session.close()

