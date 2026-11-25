"""Integration tests against the locally installed PostgreSQL and Redis.

They read the real .env and SKIP (with a reason) when a service is unreachable.
"""

import uuid
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text

from app.core.config import get_settings
from app.core.db import Database
from app.core.redis import create_redis, ping_redis

pytestmark = pytest.mark.integration


@pytest.fixture
async def database() -> AsyncIterator[Database]:
    try:
        db = Database(get_settings())
    except Exception as exc:  # any config problem means we cannot run
        pytest.skip(f"Settings not loadable from .env: {type(exc).__name__}")
    if not await db.ping():
        await db.dispose()
        pytest.skip("PostgreSQL not reachable with the credentials in .env")
    yield db
    await db.dispose()


async def test_database_ping(database: Database) -> None:
    assert await database.ping() is True


async def test_tenant_context_is_scoped_to_one_transaction(database: Database) -> None:
    tenant_id = uuid.uuid4()
    query = text("SELECT current_setting('app.tenant_id', true)")

    async with database.transaction(tenant_id) as session:
        assert (await session.execute(query)).scalar_one() == str(tenant_id)

    # A later transaction (possibly on the same pooled connection) must not see it.
    async with database.transaction(None) as session:
        assert (await session.execute(query)).scalar_one() in {None, ""}


async def test_redis_roundtrip() -> None:
    try:
        client = create_redis(get_settings())
    except Exception as exc:
        pytest.skip(f"Settings not loadable from .env: {type(exc).__name__}")
    try:
        if not await ping_redis(client):
            pytest.skip("Redis not reachable with the settings in .env")
        key = f"nexzen:test:{uuid.uuid4()}"
        await client.set(key, "ok", ex=30)
        assert await client.get(key) == "ok"
        await client.delete(key)
    finally:
        await client.aclose()
