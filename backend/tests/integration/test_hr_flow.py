"""End-to-end Neon test: Employee -> Monthly Payroll Run -> Auto GL Posting."""

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
async def hr_env() -> AsyncIterator[tuple[httpx.AsyncClient, str]]:
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
                code=f"hr-{tenant_id.hex[:8]}",
                name="Nexzen HR Test Ltd.",
            )
        )
        roles = await seed_tenant_rbac(session, tenant_id)
        admin = await UserRepository(session, tenant_id).create(
            User(
                tenant_id=tenant_id,
                email=f"hr-{tenant_id.hex[:8]}@nexzen.com",
                full_name="HR Manager",
                password_hash=hash_password("Hr-Manager-2026!"),
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
                    "payroll_lines",
                    "payroll_runs",
                    "employees",
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


async def test_employee_payroll_run_and_gl_posting_flow(
    hr_env: tuple[httpx.AsyncClient, str],
) -> None:
    client, token = hr_env
    hdr = {"Authorization": f"Bearer {token}"}

    # 1. Seed default BD Chart of Accounts
    seed_resp = await client.post("/api/v1/accounting/accounts/seed-default", headers=hdr)
    assert seed_resp.status_code == 200
    accs_resp = await client.get("/api/v1/accounting/accounts?page=1&page_size=50", headers=hdr)
    accs = {acc["code"]: acc["id"] for acc in accs_resp.json()["items"]}

    # 2. Create 2 Employees
    emp1 = await client.post(
        "/api/v1/hr/employees",
        headers=hdr,
        json={
            "employee_code": "EMP-001",
            "full_name": "Md. Rahim Uddin",
            "designation": "Senior Software Engineer",
            "department": "Engineering",
            "join_date": "2025-01-15",
            "basic_salary": "60000.00",
            "house_rent_allowance": "30000.00",
            "medical_allowance": "5000.00",
            "conveyance_allowance": "5000.00",
            "pf_deduction_percent": "10.00",
            "tax_deduction_amount": "4000.00",
        },
    )
    assert emp1.status_code == 201

    emp2 = await client.post(
        "/api/v1/hr/employees",
        headers=hdr,
        json={
            "employee_code": "EMP-002",
            "full_name": "Nusrat Jahan",
            "designation": "Accounts Executive",
            "department": "Finance",
            "join_date": "2025-06-01",
            "basic_salary": "40000.00",
            "house_rent_allowance": "20000.00",
            "pf_deduction_percent": "5.00",
            "tax_deduction_amount": "1000.00",
        },
    )
    assert emp2.status_code == 201

    # 3. Generate November 2026 Payroll Run
    run_resp = await client.post(
        "/api/v1/hr/payroll-runs",
        headers=hdr,
        json={"pay_year": 2026, "pay_month": 11, "notes": "November 2026 Salary"},
    )
    assert run_resp.status_code == 201
    run = run_resp.json()
    assert run["run_no"] == "PAY-2026-11"
    assert run["status"] == "draft"
    assert run["total_gross"] == "160000.00"
    assert run["total_deductions"] == "13000.00"
    assert run["total_net_pay"] == "147000.00"
    assert len(run["lines"]) == 2
    assert "Bangladesh Labour Act" in run["advisory_note"]

    # Duplicate period blocked
    dup_resp = await client.post(
        "/api/v1/hr/payroll-runs",
        headers=hdr,
        json={"pay_year": 2026, "pay_month": 11},
    )
    assert dup_resp.status_code == 409

    # 4. Post Payroll Run to General Ledger
    post_resp = await client.post(
        f"/api/v1/hr/payroll-runs/{run['id']}/post",
        headers=hdr,
        json={
            "salary_expense_account_id": accs["5200"],
            "payment_account_id": accs["1120"],
            "deductions_payable_account_id": accs["2210"],
        },
    )
    assert post_resp.status_code == 200
    posted = post_resp.json()
    assert posted["status"] == "posted"
    assert posted["journal_entry_id"] is not None

    # 5. Verify Trial Balance is balanced with 160,000.00 total debit/credit
    tb = (await client.get("/api/v1/accounting/reports/trial-balance", headers=hdr)).json()
    assert tb["is_balanced"] is True
    assert tb["grand_total_debit"] == "160000.00"
    assert tb["grand_total_credit"] == "160000.00"
