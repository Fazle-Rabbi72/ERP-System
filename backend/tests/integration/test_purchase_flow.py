"""End-to-end Neon test: Purchase Bill with TDS/VDS -> GL -> Payment -> Trial Balance."""

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
async def purchase_env() -> AsyncIterator[tuple[httpx.AsyncClient, str]]:
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
                code=f"purch-{tenant_id.hex[:8]}",
                name="Purchase Test Co.",
            )
        )
        roles = await seed_tenant_rbac(session, tenant_id)
        admin = await UserRepository(session, tenant_id).create(
            User(
                tenant_id=tenant_id,
                email=f"purch-{tenant_id.hex[:8]}@nexzen.com",
                full_name="Procurement Head",
                password_hash=hash_password("Purchase-Head-2026!"),
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
                    "supplier_payments",
                    "purchase_bill_lines",
                    "purchase_bills",
                    "suppliers",
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


async def test_purchase_bill_with_tds_vds_posts_to_gl_and_clears_ap_on_payment(
    purchase_env: tuple[httpx.AsyncClient, str],
) -> None:
    client, token = purchase_env
    hdr = {"Authorization": f"Bearer {token}"}

    # 1. Seed COA (1120 Bank, 1400 VAT Input, 2100 AP, 2210 TDS/VDS, 5100 COGS)
    res_seed = await client.post("/api/v1/accounting/accounts/seed-default", headers=hdr)
    assert res_seed.status_code == 200
    acc_res = await client.get("/api/v1/accounting/accounts?page=1&page_size=50", headers=hdr)
    by_code = {a["code"]: a["id"] for a in acc_res.json()["items"]}

    # 2. Create supplier
    sup_res = await client.post(
        "/api/v1/purchase/suppliers",
        headers=hdr,
        json={
            "code": "SUP-001",
            "name": "Meghna Industrial Supplies",
            "bin_no": "009876543-0201",
        },
    )
    assert sup_res.status_code == 201
    supplier_id = sup_res.json()["id"]

    # 3. Create bill: 100,000 + 15% VAT = 115,000; TDS 5% (5,000), VDS 7.5% (7,500) -> Net 102,500
    bill_res = await client.post(
        "/api/v1/purchase/bills",
        headers=hdr,
        json={
            "supplier_id": supplier_id,
            "expense_account_id": by_code["5100"],
            "supplier_bill_ref": "MIS-2026-88",
            "bill_date": "2026-11-25",
            "due_date": "2026-12-25",
            "tds_rate_percent": "5.00",
            "vds_rate_percent": "7.50",
            "lines": [
                {
                    "description": "Raw Steel Coils",
                    "quantity": "10",
                    "unit_cost": "10000.00",
                    "vat_rate_percent": "15.00",
                }
            ],
        },
    )
    assert bill_res.status_code == 201
    bill = bill_res.json()
    assert bill["net_payable"] == "102500.00"
    bill_id = bill["id"]

    # 4. Post bill -> posts balanced GL entry with TDS/VDS Payable (12,500.00)
    post_res = await client.post(f"/api/v1/purchase/bills/{bill_id}/post", headers=hdr)
    assert post_res.status_code == 200
    assert post_res.json()["status"] == "posted"

    # 5. Pay full net_payable (102,500) -> AP clears to 0.00, TDS/VDS stays 12,500.00
    pay_res = await client.post(
        f"/api/v1/purchase/bills/{bill_id}/payments",
        headers=hdr,
        json={
            "payment_date": "2026-11-25",
            "amount": "102500.00",
            "payment_method": "bank",
            "payment_account_id": by_code["1120"],
        },
    )
    assert pay_res.status_code == 201

    tb = (await client.get("/api/v1/accounting/reports/trial-balance", headers=hdr)).json()
    assert tb["is_balanced"] is True
    ap_row = next(r for r in tb["rows"] if r["code"] == "2100")
    wh_row = next(r for r in tb["rows"] if r["code"] == "2210")
    assert ap_row["net_credit"] == "0.00"
    assert wh_row["net_credit"] == "12500.00"
