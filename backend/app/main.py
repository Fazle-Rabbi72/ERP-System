"""Application factory. Run with: uvicorn app.main:create_app --factory"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api import accounting, audit, auth, health, hr, inventory, purchase, rbac, sales, vat
from app.core.config import Settings, get_settings
from app.core.db import Database
from app.core.error_handlers import register_error_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import RequestContextMiddleware
from app.core.redis import create_redis


def create_app(settings: Settings | None = None) -> FastAPI:
    active = settings or get_settings()
    configure_logging(active.log_level, json_logs=active.is_production)
    logger = get_logger(__name__)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        database = Database(active)
        redis_client = create_redis(active)
        app.state.settings = active
        app.state.database = database
        app.state.redis = redis_client
        logger.info(
            "startup",
            version=__version__,
            env=active.app_env,
            deployment_mode=active.deployment_mode,
        )
        try:
            yield
        finally:
            await redis_client.aclose()
            await database.dispose()
            logger.info("shutdown")

    app = FastAPI(
        title="Nexzen ERP",
        version=__version__,
        lifespan=lifespan,
        # Interactive docs are hidden in production to reduce attack surface.
        docs_url=None if active.is_production else "/docs",
        redoc_url=None,
        openapi_url=None if active.is_production else "/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=active.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept-Language", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(RequestContextMiddleware)
    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(auth.router, prefix=active.api_prefix)
    app.include_router(rbac.router, prefix=active.api_prefix)
    app.include_router(audit.router, prefix=active.api_prefix)
    app.include_router(accounting.router, prefix=active.api_prefix)
    app.include_router(sales.router, prefix=active.api_prefix)
    app.include_router(purchase.router, prefix=active.api_prefix)
    app.include_router(inventory.router, prefix=active.api_prefix)
    app.include_router(vat.router, prefix=active.api_prefix)
    app.include_router(hr.router, prefix=active.api_prefix)
    return app
