from arq.connections import RedisSettings
from arq.cron import cron

from app.core.config import settings
from app.db.memory_store import run_store
from app.services.retention import purge_expired_runs


async def startup(ctx):
    pass


async def shutdown(ctx):
    pass


async def run_retention_sweep(ctx):
    """Daily cron: delete research Runs older than 90 days. Never touches
    saved Prospects/Briefs — see app/services/retention.py."""
    deleted = purge_expired_runs(run_store)
    return {"deleted": deleted}


class WorkerSettings:
    functions: list = []
    cron_jobs = [cron(run_retention_sweep, hour=3, minute=0)]  # daily at 03:00
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
