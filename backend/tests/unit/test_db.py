import uuid
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import Database, set_statement_timeout, set_tenant_context
from tests.factories import make_settings

pytestmark = pytest.mark.unit


async def test_set_tenant_context_is_transaction_local() -> None:
    session = AsyncMock(spec=AsyncSession)
    tenant_id = uuid.uuid4()

    await set_tenant_context(session, tenant_id)

    session.execute.assert_awaited_once()
    call = session.execute.await_args
    assert call is not None
    statement, params = call.args
    sql = str(statement)
    assert "set_config('app.tenant_id'" in sql
    assert sql.rstrip(") ").endswith("true")
    assert params == {"tenant_id": str(tenant_id)}


async def test_ping_returns_false_when_database_unreachable() -> None:
    database = Database(make_settings(db_host="127.0.0.1", db_port=1))
    try:
        assert await database.ping() is False
    finally:
        await database.dispose()


async def test_set_statement_timeout_is_transaction_local() -> None:
    session = AsyncMock(spec=AsyncSession)
    await set_statement_timeout(session, 15000)
    call = session.execute.await_args
    assert call is not None
    statement, params = call.args
    assert "set_config('statement_timeout'" in str(statement)
    assert params == {"ms": "15000"}
