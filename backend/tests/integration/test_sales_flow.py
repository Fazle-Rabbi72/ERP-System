"""End-to-end integration test: Sales Invoice -> auto GL Posting -> Payment -> Trial Balance."""

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
async def sales_env() -> AsyncIterator[tuple[httpx.AsyncClient, str]]:
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
                code=f"sales-{tenant_id.hex[:8]}",
                name="Sales Test Co.",
            )
        )
        roles = await seed_tenant_rbac(session, tenant_id)
        admin = await UserRepository(session, tenant_id).create(
            User(
                tenant_id=tenant_id,
                email=f"sales-{tenant_id.hex[:8]}@nexzen.com",
                full_name="Sales Manager",
                password_hash=hash_password("Sales-Manager-2026!"),
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
                    "customer_payments",
                    "sales_invoice_lines",
                    "sales_invoices",
                    "customers",
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


async def test_sales_invoice_posts_to_gl_and_clears_ar_on_payment(
    sales_env: tuple[httpx.AsyncClient, str],
) -> None:
    client, token = sales_env
    hdr = {"Authorization": f"Bearer {token}"}

    # 1. Seed COA so 1110 Cash, 1200 AR, 2200 VAT Output, 4100 Sales exist
    assert (
        await client.post("/api/v1/accounting/accounts/seed-default", headers=hdr)
    ).status_code == 200
    accs = (
        await client.get("/api/v1/accounting/accounts?page=1&page_size=50", headers=hdr)
    ).json()["items"]
    cash_id = next(a["id"] for a in accs if a["code"] == "1110")

    # 2. Create a customer with Bangladesh BIN
    cust_res = await client.post(
        "/api/v1/sales/customers",
        headers=hdr,
        json={
            "code": "CUST-001",
            "name": "Padma Traders Ltd.",
            "phone": "+8801711000000",
            "bin_no": "001234567-0101",
        },
    )
    assert cust_res.status_code == 201
    customer_id = cust_res.json()["id"]

    # 3. Create draft invoice: 100,000.00 + 15% configurable VAT = 115,000.00
    inv_res = await client.post(
        "/api/v1/sales/invoices",
        headers=hdr,
        json={
            "customer_id": customer_id,
            "invoice_date": "2026-11-25",
            "due_date": "2026-12-10",
            "lines": [
                {
                    "description": "Industrial Pump",
                    "quantity": "2",
                    "unit_price": "50000.00",
                    "vat_rate_percent": "15.00",
                }
            ],
        },
    )
    assert inv_res.status_code == 201
    inv = inv_res.json()
    assert inv["subtotal"] == "100000.00"
    assert inv["vat_total"] == "15000.00"
    assert inv["grand_total"] == "115000.00"
    invoice_id = inv["id"]

    # 4. Post invoice -> automatically posts balanced GL entry
    post_res = await client.post(f"/api/v1/sales/invoices/{invoice_id}/post", headers=hdr)
    assert post_res.status_code == 200
    assert post_res.json()["status"] == "posted"
    assert post_res.json()["journal_entry_id"] is not None

    # 5. Record partial payment (50,000.00) -> status partially_paid
    p1 = await client.post(
        f"/api/v1/sales/invoices/{invoice_id}/payments",
        headers=hdr,
        json={
            "payment_date": "2026-11-25",
            "amount": "50000.00",
            "payment_method": "cash",
            "deposit_account_id": cash_id,
        },
    )
    assert p1.status_code == 201

    # 6. Overpayment must be rejected (422)
    over = await client.post(
        f"/api/v1/sales/invoices/{invoice_id}/payments",
        headers=hdr,
        json={
            "payment_date": "2026-11-25",
            "amount": "70000.00",
            "payment_method": "cash",
            "deposit_account_id": cash_id,
        },
    )
    assert over.status_code == 422

    # 7. Final payment (65,000.00) -> AR clears to 0.00 and Trial Balance stays balanced!
    p2 = await client.post(
        f"/api/v1/sales/invoices/{invoice_id}/payments",
        headers=hdr,
        json={
            "payment_date": "2026-11-25",
            "amount": "65000.00",
            "payment_method": "bank",
            "deposit_account_id": cash_id,
        },
    )
    assert p2.status_code == 201

    tb = (await client.get("/api/v1/accounting/reports/trial-balance", headers=hdr)).json()
    assert tb["is_balanced"] is True
    ar_row = next(r for r in tb["rows"] if r["code"] == "1200")
    assert ar_row["net_debit"] == "0.00"
    assert ar_row["net_credit"] == "0.00"
