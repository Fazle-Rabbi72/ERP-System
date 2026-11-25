"""End-to-end Neon test: VAT Rates + Mushak 6.1, 6.2, 6.3 and 9.1 Summary."""

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
async def vat_env() -> AsyncIterator[tuple[httpx.AsyncClient, str]]:
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
                code=f"vat-{tenant_id.hex[:8]}",
                name="Nexzen VAT Test Ltd.",
            )
        )
        roles = await seed_tenant_rbac(session, tenant_id)
        admin = await UserRepository(session, tenant_id).create(
            User(
                tenant_id=tenant_id,
                email=f"vat-{tenant_id.hex[:8]}@nexzen.com",
                full_name="VAT Officer",
                password_hash=hash_password("Vat-Officer-2026!"),
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
                    "vat_rates",
                    "supplier_payments",
                    "purchase_bill_lines",
                    "purchase_bills",
                    "suppliers",
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


async def test_mushak_61_62_63_and_91_summary_from_posted_transactions(
    vat_env: tuple[httpx.AsyncClient, str],
) -> None:
    client, token = vat_env
    hdr = {"Authorization": f"Bearer {token}"}

    # 1. Configure a VAT rate profile
    rate_res = await client.post(
        "/api/v1/vat/rates",
        headers=hdr,
        json={
            "code": "VAT-15",
            "name": "Standard Rate (Configurable)",
            "rate_percent": "15.00",
            "is_vds_applicable": True,
            "statutory_note": "Verify with VAT advisor",
        },
    )
    assert rate_res.status_code == 201

    # 2. Seed COA, create supplier & customer
    assert (
        await client.post("/api/v1/accounting/accounts/seed-default", headers=hdr)
    ).status_code == 200
    accs_resp = await client.get("/api/v1/accounting/accounts?page=1&page_size=50", headers=hdr)
    accs = accs_resp.json()["items"]
    cogs_id = next(a["id"] for a in accs if a["code"] == "5100")

    sup_id = (
        await client.post(
            "/api/v1/purchase/suppliers",
            headers=hdr,
            json={"code": "S1", "name": "Supplier One", "bin_no": "001111111-0101"},
        )
    ).json()["id"]
    cust_id = (
        await client.post(
            "/api/v1/sales/customers",
            headers=hdr,
            json={"code": "C1", "name": "Customer One", "bin_no": "002222222-0101"},
        )
    ).json()["id"]

    # 3. Post Purchase Bill: 100,000 + 15,000 Input VAT, 5,000 VDS
    bill_id = (
        await client.post(
            "/api/v1/purchase/bills",
            headers=hdr,
            json={
                "supplier_id": sup_id,
                "expense_account_id": cogs_id,
                "bill_date": "2026-11-25",
                "due_date": "2026-12-25",
                "vds_rate_percent": "5.00",
                "lines": [
                    {
                        "description": "Raw Material",
                        "quantity": "1",
                        "unit_cost": "100000.00",
                        "vat_rate_percent": "15.00",
                    }
                ],
            },
        )
    ).json()["id"]
    post_bill = await client.post(f"/api/v1/purchase/bills/{bill_id}/post", headers=hdr)
    assert post_bill.status_code == 200

    # 4. Post Sales Invoice: 200,000 + 30,000 Output VAT
    inv_id = (
        await client.post(
            "/api/v1/sales/invoices",
            headers=hdr,
            json={
                "customer_id": cust_id,
                "invoice_date": "2026-11-25",
                "due_date": "2026-12-10",
                "lines": [
                    {
                        "description": "Finished Goods",
                        "quantity": "1",
                        "unit_price": "200000.00",
                        "vat_rate_percent": "15.00",
                    }
                ],
            },
        )
    ).json()["id"]
    post_inv = await client.post(f"/api/v1/sales/invoices/{inv_id}/post", headers=hdr)
    assert post_inv.status_code == 200

    # 5. Verify Mushak 6.1, 6.2, 6.3, and 9.1
    m61 = (await client.get("/api/v1/vat/mushak/6-1", headers=hdr)).json()
    assert m61["total_input_vat"] == "15000.00"
    assert m61["total_vds"] == "5000.00"

    m62 = (await client.get("/api/v1/vat/mushak/6-2", headers=hdr)).json()
    assert m62["total_output_vat"] == "30000.00"

    m63 = (await client.get(f"/api/v1/vat/mushak/6-3/{inv_id}", headers=hdr)).json()
    assert m63["seller_name"] == "Nexzen VAT Test Ltd."
    assert m63["vat_total"] == "30000.00"

    m91 = (await client.get("/api/v1/vat/mushak/9-1", headers=hdr)).json()
    assert m91["total_output_vat"] == "30000.00"
    assert m91["total_input_vat"] == "15000.00"
    assert m91["net_vat_payable"] == "15000.00"
    assert m91["carry_forward_credit"] == "0.00"
    assert m91["total_vds_payable"] == "5000.00"
