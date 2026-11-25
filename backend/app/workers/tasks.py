"""Background tasks executed by ARQ workers.

Every task touching tenant data MUST open `database.transaction(tenant_id)`
so PostgreSQL Row-Level Security applies identically to HTTP requests.
"""

import uuid
from collections.abc import MutableMapping
from datetime import UTC, datetime

from sqlalchemy import delete
from sqlalchemy.engine import CursorResult

from app.core.db import Database
from app.core.logging import get_logger
from app.models.refresh_token import RefreshToken

logger = get_logger(__name__)


async def ping_worker(_ctx: MutableMapping[str, object]) -> dict[str, str]:
    """Lightweight liveness job to verify ARQ worker execution end-to-end."""
    return {
        "status": "ok",
        "timestamp": datetime.now(UTC).isoformat(),
    }


async def cleanup_tenant_expired_tokens(
    ctx: MutableMapping[str, object],
    tenant_id_str: str,
) -> int:
    """Purge expired refresh tokens for one tenant inside an RLS-scoped transaction."""
    database = ctx.get("database")
    if not isinstance(database, Database):
        msg = "Worker context missing Database instance."
        raise RuntimeError(msg)

    tenant_id = uuid.UUID(tenant_id_str)
    now = datetime.now(UTC)
    async with database.transaction(tenant_id) as session:
        stmt = delete(RefreshToken).where(
            RefreshToken.tenant_id == tenant_id,
            RefreshToken.expires_at < now,
        )
        result = await session.execute(stmt)
        deleted_count = (
            int(result.rowcount) if isinstance(result, CursorResult) and result.rowcount else 0
        )

    logger.info(
        "expired_refresh_tokens_cleaned",
        tenant_id=str(tenant_id),
        deleted_count=deleted_count,
    )
    return deleted_count
