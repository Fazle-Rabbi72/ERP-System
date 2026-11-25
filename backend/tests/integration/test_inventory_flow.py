"""End-to-end Neon test: Warehouses, Products, Stock In/Out & Low-Stock Alert."""

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
async def inv_env() -> AsyncIterator[tuple[httpx.AsyncClient, str]]:
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
                code=f"inv-{tenant_id.hex[:8]}",
                name="Inventory Test Co.",
            )
        )
        roles = await seed_tenant_rbac(session, tenant_id)
        admin = await UserRepository(session, tenant_id).create(
            User(
                tenant_id=tenant_id,
                email=f"inv-{tenant_id.hex[:8]}@nexzen.com",
                full_name="Store Manager",
                password_hash=hash_password("Store-Manager-2026!"),
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
                    "stock_movements",
                    "products",
                    "warehouses",
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


async def test_stock_in_out_prevents_negative_and_flags_low_stock(
    inv_env: tuple[httpx.AsyncClient, str],
) -> None:
    client, token = inv_env
    hdr = {"Authorization": f"Bearer {token}"}

    wh_res = await client.post(
        "/api/v1/inventory/warehouses",
        headers=hdr,
        json={"code": "WH-DHK", "name": "Dhaka Central Warehouse", "location": "Tejgaon, Dhaka"},
    )
    assert wh_res.status_code == 201
    wh_id = wh_res.json()["id"]

    prod_res = await client.post(
        "/api/v1/inventory/products",
        headers=hdr,
        json={
            "sku": "PUMP-5HP",
            "name": "5HP Submersible Pump",
            "unit": "pcs",
            "unit_cost": "15000.00",
            "sale_price": "22000.00",
            "reorder_level": "10.000",
        },
    )
    assert prod_res.status_code == 201
    prod_id = prod_res.json()["id"]

    # 1. Stock IN 15 pcs
    in_res = await client.post(
        "/api/v1/inventory/movements",
        headers=hdr,
        json={
            "movement_date": "2026-11-25",
            "movement_type": "in",
            "product_id": prod_id,
            "warehouse_id": wh_id,
            "quantity": "15.000",
            "reference": "GRN-001",
        },
    )
    assert in_res.status_code == 201

    # 2. Stock OUT 20 pcs MUST be blocked (negative stock forbidden -> 422)
    too_much = await client.post(
        "/api/v1/inventory/movements",
        headers=hdr,
        json={
            "movement_date": "2026-11-25",
            "movement_type": "out",
            "product_id": prod_id,
            "warehouse_id": wh_id,
            "quantity": "20.000",
        },
    )
    assert too_much.status_code == 422

    # 3. Stock OUT 8 pcs -> leaves 7 pcs (<= reorder_level 10 -> low stock alert!)
    out_res = await client.post(
        "/api/v1/inventory/movements",
        headers=hdr,
        json={
            "movement_date": "2026-11-25",
            "movement_type": "out",
            "product_id": prod_id,
            "warehouse_id": wh_id,
            "quantity": "8.000",
            "reference": "DEL-001",
        },
    )
    assert out_res.status_code == 201

    summary = (await client.get("/api/v1/inventory/stock-summary", headers=hdr)).json()
    assert summary["low_stock_count"] == 1
    assert summary["total_valuation"] == "105000.00"
    assert summary["items"][0]["is_low_stock"] is True
