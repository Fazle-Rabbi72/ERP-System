"""Integration tests proving real PostgreSQL RLS isolation and repository CRUD."""

import uuid
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.core.config import get_settings
from app.core.db import Database
from app.models.tenant import Tenant
from app.repositories.tenant import TenantRepository

pytestmark = pytest.mark.integration


@pytest.fixture
async def database() -> AsyncIterator[Database]:
    try:
        db = Database(get_settings())
    except Exception as exc:
        pytest.skip(f"Settings not loadable from .env: {type(exc).__name__}")
    if not await db.ping():
        await db.dispose()
        pytest.skip("PostgreSQL not reachable with the credentials in .env")
    yield db
    await db.dispose()


async def test_app_role_cannot_bypass_rls(database: Database) -> None:
    async with database.transaction(None) as session:
        row = (
            await session.execute(
                text(
                    "SELECT current_user, rolsuper, rolbypassrls "
                    "FROM pg_roles WHERE rolname = current_user"
                )
            )
        ).one()
        assert row.rolsuper is False
        assert row.rolbypassrls is False


async def test_rls_enforces_strict_tenant_isolation_and_fail_closed(database: Database) -> None:
    tenant_a_id = uuid.uuid4()
    tenant_b_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    code_a = f"test-a-{tenant_a_id.hex[:8]}"
    code_b = f"test-b-{tenant_b_id.hex[:8]}"

    try:
        # 1. Create Tenant A in Tenant A's transaction
        async with database.transaction(tenant_a_id) as session:
            repo_a = TenantRepository(session, tenant_a_id)
            created_a = await repo_a.create(
                Tenant(id=tenant_a_id, tenant_id=tenant_a_id, code=code_a, name="Tenant A Ltd."),
                actor_id=actor_id,
            )
            assert created_a.id == tenant_a_id

        # 2. Create Tenant B in Tenant B's transaction
        async with database.transaction(tenant_b_id) as session:
            repo_b = TenantRepository(session, tenant_b_id)
            created_b = await repo_b.create(
                Tenant(id=tenant_b_id, tenant_id=tenant_b_id, code=code_b, name="Tenant B Ltd."),
                actor_id=actor_id,
            )
            assert created_b.id == tenant_b_id

        # 3. Raw SQL (NO WHERE clause!) inside Tenant A's transaction MUST ONLY see Tenant A
        async with database.transaction(tenant_a_id) as session:
            ids = (await session.execute(text("SELECT id FROM tenants"))).scalars().all()
            assert ids == [tenant_a_id]

        # 4. Raw SQL inside a transaction with NO tenant_id MUST see ZERO rows (fail closed)
        async with database.transaction(None) as session:
            ids = (await session.execute(text("SELECT id FROM tenants"))).scalars().all()
            assert ids == []

        # 5. RLS WITH CHECK MUST reject inserting Tenant B's row inside Tenant A's transaction
        with pytest.raises(DBAPIError):
            async with database.transaction(tenant_a_id) as session:
                await session.execute(
                    text(
                        "INSERT INTO tenants (id, tenant_id, code, name) "
                        "VALUES (:id, :tid, :code, :name)"
                    ),
                    {
                        "id": tenant_b_id,
                        "tid": tenant_b_id,
                        "code": f"evil-{tenant_b_id.hex[:8]}",
                        "name": "Evil Cross-Tenant",
                    },
                )

        # 6. Soft delete hides row from default queries but preserves it with include_deleted=True
        async with database.transaction(tenant_a_id) as session:
            repo_a = TenantRepository(session, tenant_a_id)
            fetched = await repo_a.get_by_code(code_a)
            assert fetched is not None
            await repo_a.soft_delete(fetched, actor_id=actor_id)

        async with database.transaction(tenant_a_id) as session:
            repo_a = TenantRepository(session, tenant_a_id)
            assert await repo_a.get_by_id(tenant_a_id) is None
            items, total = await repo_a.list_all()
            assert items == []
            assert total == 0
            deleted_row = await repo_a.get_by_id(tenant_a_id, include_deleted=True)
            assert deleted_row is not None
            assert deleted_row.is_deleted is True
    finally:
        # Clean up test records within their own tenant transactions.
        for tid in (tenant_a_id, tenant_b_id):
            async with database.transaction(tid) as session:
                await session.execute(text("DELETE FROM tenants WHERE id = :id"), {"id": tid})
