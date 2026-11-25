"""Unit tests for BaseRepository tenant guardrails and soft delete."""

import uuid
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import PermissionDeniedError
from app.models.tenant import Tenant
from app.repositories.tenant import TenantRepository

pytestmark = pytest.mark.unit


def _make_session() -> AsyncMock:
    session = AsyncMock(spec=AsyncSession)
    session.add = lambda _obj: None
    return session


async def test_create_rejects_cross_tenant_entity() -> None:
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    repo = TenantRepository(_make_session(), tenant_a)
    entity = Tenant(id=tenant_b, tenant_id=tenant_b, code="b", name="Tenant B")

    with pytest.raises(PermissionDeniedError):
        await repo.create(entity)


async def test_create_sets_tenant_and_actor_fields() -> None:
    tenant_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    session = _make_session()
    repo = TenantRepository(session, tenant_id)
    entity = Tenant(id=tenant_id, code="acme", name="Acme BD Ltd.")

    created = await repo.create(entity, actor_id=actor_id)

    assert created.tenant_id == tenant_id
    assert created.created_by == actor_id
    assert created.updated_by == actor_id
    session.flush.assert_awaited_once()
    session.refresh.assert_awaited_once_with(entity)


async def test_update_rejects_cross_tenant_entity() -> None:
    repo = TenantRepository(_make_session(), uuid.uuid4())
    other = uuid.uuid4()
    entity = Tenant(id=other, tenant_id=other, code="other", name="Other")

    with pytest.raises(PermissionDeniedError):
        await repo.update(entity)


async def test_soft_delete_marks_deleted_and_sets_actor() -> None:
    tenant_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    session = _make_session()
    repo = TenantRepository(session, tenant_id)
    entity = Tenant(id=tenant_id, tenant_id=tenant_id, code="del", name="To Delete")

    deleted = await repo.soft_delete(entity, actor_id=actor_id)

    assert deleted.is_deleted is True
    assert deleted.updated_by == actor_id
    assert deleted.updated_at is not None
    session.flush.assert_awaited_once()


async def test_soft_delete_rejects_cross_tenant_entity() -> None:
    repo = TenantRepository(_make_session(), uuid.uuid4())
    other = uuid.uuid4()
    entity = Tenant(id=other, tenant_id=other, code="other", name="Other")

    with pytest.raises(PermissionDeniedError):
        await repo.soft_delete(entity)
