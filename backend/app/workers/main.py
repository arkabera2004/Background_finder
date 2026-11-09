from datetime import datetime, timezone

from arq.connections import RedisSettings
from arq.cron import cron

from app.api.routers.chanakya.catalogue import create_run as submit_run
from app.api.routers.chanakya.catalogue import submit_offering_brief
from app.api.routers.chanakya.orchestrator import orchestrate_run
from app.core.auth import AuthenticatedUser
from app.core.config import settings
from app.db.chanakya_repository import ChanakyaRunRepository
from app.db.memory_store import run_store
from app.db.session import get_session
from app.schemas.catalogue import MonthlyRunCreate, OfferingBriefInput, OfferingInput
from app.services.retention import purge_expired_runs


async def startup(ctx):
    pass


async def shutdown(ctx):
    pass


async def run_retention_sweep(ctx):
    """Daily cron: delete research Runs older than 90 days. Never touches
    saved Prospects/Briefs — see app/services/retention.py. Also purges
    Chanakya MonthlyRuns past the same retention window — cascade delete
    takes every stage/company/person/email/brief/QA record under them."""
    deleted = purge_expired_runs(run_store)
    session = get_session()
    try:
        chanakya_deleted = ChanakyaRunRepository(session).purge_expired_runs(
            settings.default_retention_days
        )
    finally:
        session.close()
    return {"deleted": deleted, "chanakya_deleted": chanakya_deleted}


async def run_due_chanakya_schedules(ctx):
    """Daily cron: Phase 5 durable monthly scheduler. For every tenant's
    enabled `ChanakyaSchedule` whose trigger day has passed and that
    hasn't already produced a run this period, creates the run, submits
    its stored offering/ICP brief, and drives it through the same
    idempotent, resumable orchestrator used by the manual HTTP path.

    Failure isolation: one tenant's exception is caught, recorded on its
    schedule row, and never stops the remaining tenants from running.
    Duplicate prevention: `due_schedules()` excludes any schedule whose
    `last_run_period` already matches, and `create_run` itself rejects a
    second run for the same (owner, period) with a 409 the scheduler
    treats as already-done, not a failure.
    """
    now = datetime.now(timezone.utc)
    period = now.strftime("%Y-%m")
    session = get_session()
    results = []
    try:
        repo = ChanakyaRunRepository(session)
        for schedule in repo.due_schedules(now.day, period):
            user = AuthenticatedUser(user_id=schedule.owner_id, email=None)
            try:
                run_dict = await submit_run(
                    MonthlyRunCreate(period=period, config=schedule.config), user
                )
                run_id = run_dict["id"]
                await submit_offering_brief(
                    run_id,
                    OfferingBriefInput(
                        offerings=[OfferingInput(**o) for o in schedule.offerings],
                        filters=schedule.filters,
                    ),
                    user,
                )
                outcome = await orchestrate_run(run_id, user)
                repo.record_schedule_run(
                    schedule, period, run_id, status=outcome.get("stopped_at") and "stopped" or "completed"
                )
                results.append({"schedule_id": schedule.id, "run_id": run_id, "status": "ok"})
            except Exception as exc:  # noqa: BLE001 - one tenant's failure must not block the rest
                repo.record_schedule_run(schedule, period, None, status="failed", error=str(exc))
                results.append({"schedule_id": schedule.id, "status": "failed", "error": str(exc)})
    finally:
        session.close()
    return {"period": period, "results": results}


class WorkerSettings:
    functions: list = []
    cron_jobs = [
        cron(run_retention_sweep, hour=3, minute=0),  # daily at 03:00
        cron(run_due_chanakya_schedules, hour=4, minute=0),  # daily at 04:00
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
