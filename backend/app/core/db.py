"""Async PostgreSQL access with tenant context for Row-Level Security (RLS).

Every transaction that touches tenant data must be opened through
`Database.transaction(tenant_id)`. The tenant id and statement timeout are set
with `set_config(..., true)`, so they live only inside that transaction. This is
what makes the design safe behind a transaction-mode pooler such as Neon's
PgBouncer: no session-level state is ever relied upon, and nothing leaks to
another request. RLS policies (added in step F3) read
`current_setting('app.tenant_id', true)`.
"""

import ssl
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def build_ssl_context(mode: str) -> ssl.SSLContext | None:
    """Translate DB_SSL_MODE into an SSL context for asyncpg.

    disable      -> no TLS (only acceptable for a local database)
    require      -> encrypted, certificate not verified
    verify-full  -> encrypted, certificate and hostname verified (recommended)
    """
    if mode == "disable":
        return None
    context = ssl.create_default_context()
    if mode == "require":
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    return context


async def set_tenant_context(session: AsyncSession, tenant_id: uuid.UUID) -> None:
    """Bind the tenant to the current transaction (transaction-local)."""
    await session.execute(
        text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
        {"tenant_id": str(tenant_id)},
    )


async def set_statement_timeout(session: AsyncSession, milliseconds: int) -> None:
    """Limit statement run time for the current transaction (transaction-local)."""
    await session.execute(
        text("SELECT set_config('statement_timeout', :ms, true)"),
        {"ms": str(milliseconds)},
    )


class Database:
    """Owns the engine and hands out transactional sessions."""

    def __init__(self, settings: Settings) -> None:
        connect_args: dict[str, object] = {
            "statement_cache_size": settings.db_statement_cache_size,
        }
        ssl_context = build_ssl_context(settings.db_ssl_mode)
        if ssl_context is not None:
            connect_args["ssl"] = ssl_context
        self._statement_timeout_ms = settings.db_statement_timeout_ms
        self._engine: AsyncEngine = create_async_engine(
            settings.database_url,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_timeout=settings.db_pool_timeout_seconds,
            # Serverless Postgres (e.g. Neon) suspends idle compute and drops
            # connections; pre-ping and recycling replace stale ones transparently.
            pool_pre_ping=True,
            pool_recycle=settings.db_pool_recycle_seconds,
            connect_args=connect_args,
        )
        self._sessionmaker: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self._engine,
            expire_on_commit=False,
        )

    @asynccontextmanager
    async def transaction(self, tenant_id: uuid.UUID | None) -> AsyncIterator[AsyncSession]:
        """Open a session inside one transaction: commit on success, roll back on error.

        Pass `tenant_id=None` only for the few operations that legitimately run
        without a tenant (e.g. resolving a tenant at login). With RLS enabled,
        such a session sees no tenant rows, so it fails closed.
        """
        async with self._sessionmaker() as session, session.begin():
            await set_statement_timeout(session, self._statement_timeout_ms)
            if tenant_id is not None:
                await set_tenant_context(session, tenant_id)
            yield session

    async def ping(self) -> bool:
        """True if the database answers a trivial query. Never raises."""
        try:
            async with self._engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        except (SQLAlchemyError, OSError, TimeoutError):
            logger.warning("database_ping_failed")
            return False
        return True

    async def dispose(self) -> None:
        await self._engine.dispose()
