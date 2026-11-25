"""ARQ worker configuration and lifecycle hooks.

Run locally: `make worker` (or `python -m arq app.workers.settings.WorkerSettings`)
Run in Linux production: `infra/systemd/nexzen-worker.service`
"""

from collections.abc import MutableMapping
from typing import ClassVar

from arq.connections import RedisSettings

from app.core.config import Settings, get_settings
from app.core.db import Database
from app.core.logging import configure_logging, get_logger
from app.workers.tasks import cleanup_tenant_expired_tokens, ping_worker

logger = get_logger(__name__)


def build_arq_redis_settings(settings: Settings) -> RedisSettings:
    """Translate application Settings into ARQ's RedisSettings (supports TLS)."""
    password = settings.redis_password.get_secret_value() if settings.redis_password else None
    return RedisSettings(
        host=settings.redis_host,
        port=settings.redis_port,
        database=settings.redis_db,
        password=password,
        ssl=settings.redis_ssl,
    )


async def on_startup(ctx: MutableMapping[str, object]) -> None:
    settings = get_settings()
    configure_logging(settings.log_level, json_logs=settings.is_production)
    ctx["settings"] = settings
    ctx["database"] = Database(settings)
    logger.info(
        "worker_startup",
        env=settings.app_env,
        deployment_mode=settings.deployment_mode,
        poll_delay=settings.arq_poll_delay_seconds,
    )


async def on_shutdown(ctx: MutableMapping[str, object]) -> None:
    database = ctx.get("database")
    if isinstance(database, Database):
        await database.dispose()
    logger.info("worker_shutdown")


_settings = get_settings()


class WorkerSettings:
    """Entrypoint loaded by `arq app.workers.settings.WorkerSettings`."""

    redis_settings = build_arq_redis_settings(_settings)
    functions: ClassVar[list[object]] = [ping_worker, cleanup_tenant_expired_tokens]
    on_startup = on_startup
    on_shutdown = on_shutdown
    poll_delay = _settings.arq_poll_delay_seconds
    max_jobs = _settings.arq_max_jobs
    job_timeout = 300
    keep_result = 3600
