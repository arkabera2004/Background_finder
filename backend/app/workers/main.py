from arq.connections import RedisSettings
from arq.cron import cron

from app.core.config import settings
from app.db.chanakya_repository import ChanakyaRunRepository
from app.db.memory_store import run_store
from app.db.session import get_session
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


class WorkerSettings:
    functions: list = []
    cron_jobs = [cron(run_retention_sweep, hour=3, minute=0)]  # daily at 03:00
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
