"""Integration tests for Accounting & GL on real Neon PostgreSQL (COA, Journals, Trial Balance)."""

import uuid
from collections.abc import AsyncIterator

import httpx
import pytest
from sqlalchemy import text

from app.core.config import get_settings
from app.core.db import Database
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
async def gl_env() -> AsyncIterator[tuple[httpx.AsyncClient, str]]:
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
    async with db.transaction(tenant_id) as session:
        await TenantRepository(session, tenant_id).create(
            Tenant(
                id=tenant_id,
                tenant_id=tenant_id,
                code=f"gl-{tenant_id.hex[:8]}",
                name="GL Test Co.",
            )
        )
        roles = await seed_tenant_rbac(session, tenant_id)
        admin = await UserRepository(session, tenant_id).create(
            User(
                tenant_id=tenant_id,
                email=f"gl-{tenant_id.hex[:8]}@nexzen.com",
                full_name="Chief Accountant",
                password_hash=hash_password("GL-Accountant-2026!"),
            )
        )
        await RoleRepository(session, tenant_id).assign_to_user(
            admin.id, roles["tenant_admin"].id, actor_id=admin.id
        )

    token, _ = create_access_token(settings, user_id=admin.id, tenant_id=tenant_id)
    app = create_app(settings)
    app.state.settings = settings
    app.state.database = db
    app.state.redis = redis

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        try:
            yield client, token
        finally:
            async with db.transaction(tenant_id) as session:
                for table in (
                    "journal_lines",
                    "journal_entries",
                    "accounts",
                    "user_roles",
                    "role_permissions",
                    "roles",
                    "permissions",
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


async def test_coa_journal_post_reverse_and_trial_balance(
    gl_env: tuple[httpx.AsyncClient, str],
) -> None:
    client, token = gl_env
    hdr = {"Authorization": f"Bearer {token}"}

    # 1. Seed default Bangladesh SME Chart of Accounts (idempotent)
    seed_res = await client.post("/api/v1/accounting/accounts/seed-default", headers=hdr)
    assert seed_res.status_code == 200
    assert seed_res.json()["created_count"] >= 15

    # 2. Fetch Cash (1110) and Sales Revenue (4100) accounts
    acc_res = await client.get("/api/v1/accounting/accounts?page=1&page_size=50", headers=hdr)
    assert acc_res.status_code == 200
    by_code = {item["code"]: item["id"] for item in acc_res.json()["items"]}
    cash_id = by_code["1110"]
    sales_id = by_code["4100"]
    assets_group_id = by_code["1000"]

    # 3. Reject posting to a group account
    bad_group = await client.post(
        "/api/v1/accounting/journals",
        headers=hdr,
        json={
            "entry_date": "2026-11-25",
            "narration": "Invalid group posting",
            "lines": [
                {"account_id": assets_group_id, "debit": "500.00"},
                {"account_id": sales_id, "credit": "500.00"},
            ],
        },
    )
    assert bad_group.status_code == 422

    # 4. Create balanced draft journal entry (BDT 2,50,000.50)
    create_res = await client.post(
        "/api/v1/accounting/journals",
        headers=hdr,
        json={
            "entry_date": "2026-11-25",
            "reference": "INV-001",
            "narration": "Cash sale to Dhaka distributor",
            "lines": [
                {"account_id": cash_id, "description": "Cash received", "debit": "250000.50"},
                {"account_id": sales_id, "description": "Sales income", "credit": "250000.50"},
            ],
        },
    )
    assert create_res.status_code == 201
    entry = create_res.json()
    assert entry["status"] == "draft"
    entry_id = entry["id"]

    # 5. Draft entries must NOT appear in Trial Balance yet
    tb_before = await client.get("/api/v1/accounting/reports/trial-balance", headers=hdr)
    assert tb_before.status_code == 200
    assert tb_before.json()["grand_total_debit"] == "0.00"

    # 6. Post journal entry -> appears in Trial Balance with exact Decimal balance
    post_res = await client.post(f"/api/v1/accounting/journals/{entry_id}/post", headers=hdr)
    assert post_res.status_code == 200
    assert post_res.json()["status"] == "posted"

    tb_after = await client.get("/api/v1/accounting/reports/trial-balance", headers=hdr)
    assert tb_after.status_code == 200
    tb = tb_after.json()
    assert tb["is_balanced"] is True
    assert tb["grand_total_debit"] == "250000.50"
    assert tb["grand_total_credit"] == "250000.50"

    # 7. Reverse posted entry -> creates counter-entry, net balance returns to 0.00
    rev_res = await client.post(f"/api/v1/accounting/journals/{entry_id}/reverse", headers=hdr)
    assert rev_res.status_code == 200
    assert rev_res.json()["reversed_entry_id"] == entry_id

    tb_rev = await client.get("/api/v1/accounting/reports/trial-balance", headers=hdr)
    assert tb_rev.status_code == 200
    for row in tb_rev.json()["rows"]:
        assert row["net_debit"] == "0.00"
        assert row["net_credit"] == "0.00"
