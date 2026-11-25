"""Integration tests proving audit log recording, RBAC gating, and DB-level immutability."""

import uuid
from collections.abc import AsyncIterator

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.core.config import get_settings
from app.core.db import Database
from app.core.permissions import PERM_RBAC_ROLES_READ
from app.core.redis import create_redis, ping_redis
from app.core.security import create_access_token, hash_password
from app.main import create_app
from app.models.tenant import Tenant
from app.models.user import User
from app.repositories.rbac import RoleRepository
from app.repositories.tenant import TenantRepository
from app.repositories.user import UserRepository
from app.services.rbac_service import seed_tenant_rbac

pytestmark = pytest.mark.integration


@pytest.fixture
async def audit_env() -> AsyncIterator[tuple[httpx.AsyncClient, Database, uuid.UUID, str, str]]:
    try:
        settings = get_settings()
        db = Database(settings)
        redis = create_redis(settings)
    except Exception as exc:
        pytest.skip(f"Settings not loadable from .env: {type(exc).__name__}")

    if not await db.ping() or not await ping_redis(redis):
        await redis.aclose()
        await db.dispose()
        pytest.skip("PostgreSQL or Redis not reachable with .env credentials")

    tenant_id = uuid.uuid4()
    pw_hash = hash_password("Audit-Test-Pass-2026!")

    async with db.transaction(tenant_id) as session:
        await TenantRepository(session, tenant_id).create(
            Tenant(
                id=tenant_id,
                tenant_id=tenant_id,
                code=f"audit-{tenant_id.hex[:8]}",
                name="Audit Test Co.",
            )
        )
        roles = await seed_tenant_rbac(session, tenant_id)
        user_repo = UserRepository(session, tenant_id)
        admin = await user_repo.create(
            User(
                tenant_id=tenant_id,
                email=f"admin-{tenant_id.hex[:8]}@nexzen.com",
                full_name="Audit Admin",
                password_hash=pw_hash,
            )
        )
        viewer = await user_repo.create(
            User(
                tenant_id=tenant_id,
                email=f"viewer-{tenant_id.hex[:8]}@nexzen.com",
                full_name="Audit Viewer",
                password_hash=pw_hash,
            )
        )
        role_repo = RoleRepository(session, tenant_id)
        await role_repo.assign_to_user(admin.id, roles["tenant_admin"].id, actor_id=admin.id)
        await role_repo.assign_to_user(viewer.id, roles["viewer"].id, actor_id=admin.id)

    admin_token, _ = create_access_token(settings, user_id=admin.id, tenant_id=tenant_id)
    viewer_token, _ = create_access_token(settings, user_id=viewer.id, tenant_id=tenant_id)

    app = create_app(settings)
    app.state.settings = settings
    app.state.database = db
    app.state.redis = redis

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        try:
            yield client, db, tenant_id, admin_token, viewer_token
        finally:
            # Note: audit_logs rows are intentionally immutable and cannot be deleted;
            # they remain strictly isolated under this ephemeral test tenant_id via RLS.
            async with db.transaction(tenant_id) as session:
                for table in ("user_roles", "role_permissions", "roles", "permissions", "users"):
                    await session.execute(
                        text(f'DELETE FROM "{table}" WHERE tenant_id = :tid'),  # noqa: S608
                        {"tid": tenant_id},
                    )
                await session.execute(
                    text("DELETE FROM tenants WHERE id = :tid"),
                    {"tid": tenant_id},
                )
            await redis.aclose()
            await db.dispose()


async def test_audit_log_recording_querying_and_db_immutability(
    audit_env: tuple[httpx.AsyncClient, Database, uuid.UUID, str, str],
) -> None:
    client, db, tenant_id, admin_token, viewer_token = audit_env
    admin_hdr = {"Authorization": f"Bearer {admin_token}", "X-Request-ID": "audit-req-001"}
    viewer_hdr = {"Authorization": f"Bearer {viewer_token}"}

    # 1. Viewer lacks audit.read -> 403
    denied = await client.get("/api/v1/audit-logs", headers=viewer_hdr)
    assert denied.status_code == 403

    # 2. Admin creates a role -> triggers atomic audit log write with request_id
    create_res = await client.post(
        "/api/v1/rbac/roles",
        headers=admin_hdr,
        json={
            "code": "cashier",
            "name": "Cashier",
            "description": "POS Cashier",
            "permission_codes": [PERM_RBAC_ROLES_READ],
        },
    )
    assert create_res.status_code == 201
    role_id = create_res.json()["id"]

    # 3. Admin queries audit logs filtered by action
    list_res = await client.get(
        "/api/v1/audit-logs?action=rbac.role.created&page=1&page_size=10",
        headers=admin_hdr,
    )
    assert list_res.status_code == 200
    body = list_res.json()
    assert body["meta"]["total"] == 1
    entry = body["items"][0]
    assert entry["resource_type"] == "role"
    assert entry["resource_id"] == role_id
    assert entry["after_data"]["code"] == "cashier"
    assert entry["request_id"] == "audit-req-001"

    # 4. DB-level immutability: UPDATE and DELETE MUST be rejected by PostgreSQL trigger!
    entry_id = uuid.UUID(entry["id"])
    with pytest.raises(DBAPIError, match="append-only"):
        async with db.transaction(tenant_id) as session:
            await session.execute(
                text("UPDATE audit_logs SET action = 'tampered' WHERE id = :id"),
                {"id": entry_id},
            )

    with pytest.raises(DBAPIError, match="append-only"):
        async with db.transaction(tenant_id) as session:
            await session.execute(
                text("DELETE FROM audit_logs WHERE id = :id"),
                {"id": entry_id},
            )
