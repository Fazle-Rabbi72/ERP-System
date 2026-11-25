"""End-to-end integration tests for RBAC enforcement, role creation, assignment & pagination."""

import uuid
from collections.abc import AsyncIterator

import httpx
import pytest
from sqlalchemy import text

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
async def rbac_env() -> AsyncIterator[tuple[httpx.AsyncClient, str, str, uuid.UUID]]:
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
    pw_hash = hash_password("Test-Password-2026!")

    async with db.transaction(tenant_id) as session:
        await TenantRepository(session, tenant_id).create(
            Tenant(
                id=tenant_id,
                tenant_id=tenant_id,
                code=f"rbac-{tenant_id.hex[:8]}",
                name="RBAC Test Co.",
            )
        )
        roles = await seed_tenant_rbac(session, tenant_id)
        user_repo = UserRepository(session, tenant_id)
        admin = await user_repo.create(
            User(
                tenant_id=tenant_id,
                email=f"admin-{tenant_id.hex[:8]}@nexzen.com",
                full_name="Admin User",
                password_hash=pw_hash,
            )
        )
        viewer = await user_repo.create(
            User(
                tenant_id=tenant_id,
                email=f"viewer-{tenant_id.hex[:8]}@nexzen.com",
                full_name="Viewer User",
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
            yield client, admin_token, viewer_token, viewer.id
        finally:
            async with db.transaction(tenant_id) as session:
                for table in (
                    "user_roles",
                    "role_permissions",
                    "roles",
                    "permissions",
                    "refresh_tokens",
                    "users",
                ):
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


async def test_rbac_enforcement_role_lifecycle_and_pagination(
    rbac_env: tuple[httpx.AsyncClient, str, str, uuid.UUID],
) -> None:
    client, admin_token, viewer_token, viewer_id = rbac_env
    admin_hdr = {"Authorization": f"Bearer {admin_token}"}
    viewer_hdr = {"Authorization": f"Bearer {viewer_token}"}

    # 1. Viewer lacks rbac.roles.read and rbac.roles.write -> 403
    denied_list = await client.get("/api/v1/rbac/roles", headers=viewer_hdr)
    assert denied_list.status_code == 403
    assert denied_list.json()["error"]["code"] == "permission_denied"

    denied_create = await client.post(
        "/api/v1/rbac/roles",
        headers=viewer_hdr,
        json={"code": "hacker", "name": "Hacker", "permission_codes": []},
    )
    assert denied_create.status_code == 403

    # 2. Admin lists roles with pagination, sorting, and filtering
    roles_res = await client.get(
        "/api/v1/rbac/roles?page=1&page_size=2&sort_by=code&sort_dir=asc",
        headers=admin_hdr,
    )
    assert roles_res.status_code == 200
    body = roles_res.json()
    assert body["meta"]["total"] == 3
    assert body["meta"]["total_pages"] == 2
    assert body["meta"]["has_next"] is True
    assert len(body["items"]) == 2

    # 3. Admin creates a custom role granting rbac.roles.read
    create_res = await client.post(
        "/api/v1/rbac/roles",
        headers=admin_hdr,
        json={
            "code": "role_reader",
            "name": "Role Reader",
            "description": "Can inspect roles",
            "permission_codes": [PERM_RBAC_ROLES_READ],
        },
    )
    assert create_res.status_code == 201
    new_role_id = create_res.json()["id"]

    # 4. Admin assigns the new role to viewer -> viewer immediately gains access
    assign_res = await client.post(
        f"/api/v1/rbac/users/{viewer_id}/roles/{new_role_id}",
        headers=admin_hdr,
    )
    assert assign_res.status_code == 204

    allowed_list = await client.get("/api/v1/rbac/roles?search=Role%20Reader", headers=viewer_hdr)
    assert allowed_list.status_code == 200
    assert allowed_list.json()["meta"]["total"] == 1

    # 5. Admin revokes the role -> viewer loses access immediately
    revoke_res = await client.delete(
        f"/api/v1/rbac/users/{viewer_id}/roles/{new_role_id}",
        headers=admin_hdr,
    )
    assert revoke_res.status_code == 204
    denied_again = await client.get("/api/v1/rbac/roles", headers=viewer_hdr)
    assert denied_again.status_code == 403
