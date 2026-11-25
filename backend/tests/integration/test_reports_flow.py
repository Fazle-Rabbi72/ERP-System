"""End-to-end Neon test: P&L, Balance Sheet & Executive Dashboard Summary."""

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
async def reports_env() -> AsyncIterator[tuple[httpx.AsyncClient, str]]:
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
                code=f"rep-{tenant_id.hex[:8]}",
                name="Nexzen Reports Test Ltd.",
            )
        )
        roles = await seed_tenant_rbac(session, tenant_id)
        admin = await UserRepository(session, tenant_id).create(
            User(
                tenant_id=tenant_id,
                email=f"rep-{tenant_id.hex[:8]}@nexzen.com",
                full_name="CFO User",
                password_hash=hash_password("Reports-CFO-2026!"),
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


async def test_financial_statements_and_dashboard_summary(
    reports_env: tuple[httpx.AsyncClient, str],
) -> None:
    client, token = reports_env
    hdr = {"Authorization": f"Bearer {token}"}

    seed_resp = await client.post("/api/v1/accounting/accounts/seed-default", headers=hdr)
    assert seed_resp.status_code == 200
    accs_resp = await client.get("/api/v1/accounting/accounts?page=1&page_size=50", headers=hdr)
    accs = {a["code"]: a["id"] for a in accs_resp.json()["items"]}

    # Post revenue journal: DR Cash 150,000 / CR Sales 150,000
    jv1 = (
        await client.post(
            "/api/v1/accounting/journals",
            headers=hdr,
            json={
                "entry_date": "2026-11-10",
                "reference": "SALE-1",
                "narration": "Cash sales revenue",
                "lines": [
                    {"account_id": accs["1110"], "debit": "150000.00", "credit": "0.00"},
                    {"account_id": accs["4100"], "debit": "0.00", "credit": "150000.00"},
                ],
            },
        )
    ).json()["id"]
    post1 = await client.post(f"/api/v1/accounting/journals/{jv1}/post", headers=hdr)
    assert post1.status_code == 200

    # Post expense journal: DR Salaries 60,000 / CR Cash 60,000
    jv2 = (
        await client.post(
            "/api/v1/accounting/journals",
            headers=hdr,
            json={
                "entry_date": "2026-11-20",
                "reference": "EXP-1",
                "narration": "Office salary paid",
                "lines": [
                    {"account_id": accs["5200"], "debit": "60000.00", "credit": "0.00"},
                    {"account_id": accs["1110"], "debit": "0.00", "credit": "60000.00"},
                ],
            },
        )
    ).json()["id"]
    post2 = await client.post(f"/api/v1/accounting/journals/{jv2}/post", headers=hdr)
    assert post2.status_code == 200

    # 1. Profit & Loss
    pnl = (await client.get("/api/v1/reports/profit-and-loss", headers=hdr)).json()
    assert pnl["total_revenue"] == "150000.00"
    assert pnl["total_expense"] == "60000.00"
    assert pnl["net_profit"] == "90000.00"

    # 2. Balance Sheet (Cash = 90,000 == Current Earnings 90,000)
    bs = (await client.get("/api/v1/reports/balance-sheet", headers=hdr)).json()
    assert bs["total_assets"] == "90000.00"
    assert bs["current_earnings"] == "90000.00"
    assert bs["total_liabilities_and_equity"] == "90000.00"
    assert bs["is_balanced"] is True

    # 3. Dashboard Summary
    dash = (await client.get("/api/v1/reports/dashboard-summary", headers=hdr)).json()
    assert dash["total_revenue"] == "150000.00"
    assert dash["net_profit"] == "90000.00"
    assert dash["total_assets"] == "90000.00"
    assert dash["total_accounts_count"] >= 10
