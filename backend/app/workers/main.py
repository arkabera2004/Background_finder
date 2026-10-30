from arq.connections import RedisSettings

from app.core.config import settings


async def startup(ctx):
    pass


async def shutdown(ctx):
    pass


class WorkerSettings:
    functions: list = []
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
