"""Idempotent rich Bangladeshi business demo data seeder for Nexzen ERP.

Populates realistic end-to-end data across all 7 modules (Accounting, Sales,
Purchase, Inventory, VAT/Mushak, HR/Payroll, Reports & RBAC) using the real
service layer so every GL journal and audit log is 100% authentic.

Usage:
    python -m app.seed_demo
"""

import asyncio
import contextlib
import os
import sys
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select, text

from app.core.config import get_settings
from app.core.db import Database
from app.core.exceptions import ConflictError
from app.core.query import PaginationParams, SortParams
from app.core.security import hash_password
from app.models.tenant import Tenant
from app.models.user import User
from app.repositories.accounting import AccountRepository
from app.repositories.hr import EmployeeRepository, PayrollRunRepository
from app.repositories.inventory import ProductRepository, WarehouseRepository
from app.repositories.purchase import PurchaseBillRepository, SupplierRepository
from app.repositories.rbac import RoleRepository
from app.repositories.sales import CustomerRepository, SalesInvoiceRepository
from app.repositories.user import UserRepository
from app.repositories.vat import VatRateRepository
from app.schemas.accounting import JournalLineCreateRequest
from app.schemas.purchase import PurchaseBillLineCreateRequest
from app.schemas.sales import InvoiceLineCreateRequest
from app.services.accounting_service import AccountingService
from app.services.hr_service import HrService
from app.services.inventory_service import InventoryService
from app.services.purchase_service import PurchaseService
from app.services.rbac_service import seed_tenant_rbac
from app.services.sales_service import SalesService
from app.services.vat_service import VatService


async def _ensure_auditor_user(db: Database, tenant_id: uuid.UUID, actor_id: uuid.UUID) -> None:
    auditor_email = "auditor@nexzen.com"
    async with db.transaction(tenant_id) as session:
        user_repo = UserRepository(session, tenant_id)
        if await user_repo.get_by_email(auditor_email) is not None:
            return
        roles = await seed_tenant_rbac(session, tenant_id)
        auditor = await user_repo.create(
            User(
                tenant_id=tenant_id,
                email=auditor_email,
                full_name="Samira Rahman (Auditor)",
                password_hash=hash_password("NexzenAudit!2026"),
                is_active=True,
            ),
            actor_id=actor_id,
        )
        await RoleRepository(session, tenant_id).assign_to_user(
            auditor.id, roles["auditor"].id, actor_id=actor_id
        )


async def _seed_accounting(
    db: Database, tenant_id: uuid.UUID, actor_id: uuid.UUID
) -> dict[str, uuid.UUID]:
    acc_svc = AccountingService(db)
    await acc_svc.seed_default_coa(tenant_id=tenant_id, actor_id=actor_id)
    async with db.transaction(tenant_id) as session:
        accounts, _ = await AccountRepository(session, tenant_id).list_all(offset=0, limit=100)
        acc_by_code = {a.code: a.id for a in accounts}

    demo_journals: list[tuple[str, date, str, list[tuple[str, str, str]]]] = [
        (
            "DEMO-CAP-2026",
            date(2026, 9, 1),
            "Opening share capital deposited into main bank account",
            [("1120", "1500000.00", "0.00"), ("3100", "0.00", "1500000.00")],
        ),
        (
            "DEMO-REV-2026-09",
            date(2026, 9, 20),
            "September 2026 corporate IT & consulting revenue",
            [("1120", "420000.00", "0.00"), ("4200", "0.00", "420000.00")],
        ),
        (
            "DEMO-EXP-2026-09",
            date(2026, 9, 28),
            "September 2026 office rent, utilities & operational expenses",
            [("5300", "135000.00", "0.00"), ("1120", "0.00", "135000.00")],
        ),
        (
            "DEMO-REV-2026-10",
            date(2026, 10, 18),
            "October 2026 enterprise software & hardware sales",
            [("1120", "580000.00", "0.00"), ("4100", "0.00", "580000.00")],
        ),
        (
            "DEMO-EXP-2026-10",
            date(2026, 10, 27),
            "October 2026 office rent & utilities",
            [("5300", "145000.00", "0.00"), ("1120", "0.00", "145000.00")],
        ),
        (
            "DEMO-EXP-2026-11",
            date(2026, 11, 10),
            "November 2026 Dhaka office rent & internet",
            [("5300", "150000.00", "0.00"), ("1120", "0.00", "150000.00")],
        ),
    ]
    existing_entries, _ = await acc_svc.list_journal_entries(
        tenant_id=tenant_id,
        pagination=PaginationParams(page=1, page_size=100),
        sort=SortParams(),
    )
    existing_refs = {e.reference for e in existing_entries}
    for ref, jdate, narr, lines in demo_journals:
        if ref in existing_refs:
            continue
        entry = await acc_svc.create_journal_entry(
            tenant_id=tenant_id,
            actor_id=actor_id,
            entry_date=jdate,
            reference=ref,
            narration=narr,
            lines=[
                JournalLineCreateRequest(
                    account_id=acc_by_code[code],
                    description=narr,
                    debit=Decimal(dr),
                    credit=Decimal(cr),
                )
                for code, dr, cr in lines
            ],
        )
        await acc_svc.post_journal_entry(tenant_id=tenant_id, actor_id=actor_id, entry_id=entry.id)
    return acc_by_code


async def _seed_vat(db: Database, tenant_id: uuid.UUID, actor_id: uuid.UUID) -> None:
    vat_svc = VatService(db)
    demo_rates = [
        ("VAT-15", "Standard VAT 15%", Decimal("15.00"), False, "Standard supply rate"),
        (
            "VAT-7.5",
            "Reduced VAT 7.5% (VDS)",
            Decimal("7.50"),
            True,
            "Verify applicable SRO with tax advisor",
        ),
        ("VAT-0", "Zero-Rated Export 0%", Decimal("0.00"), False, "Export supply"),
    ]
    for code, name, pct, vds, note in demo_rates:
        async with db.transaction(tenant_id) as session:
            exists = await VatRateRepository(session, tenant_id).get_by_code(code)
        if exists is None:
            await vat_svc.create_rate(
                tenant_id=tenant_id,
                actor_id=actor_id,
                code=code,
                name=name,
                rate_percent=pct,
                is_vds_applicable=vds,
                statutory_note=note,
            )


async def _seed_sales(
    db: Database,
    tenant_id: uuid.UUID,
    actor_id: uuid.UUID,
    acc_by_code: dict[str, uuid.UUID],
) -> None:
    sales_svc = SalesService(db)
    demo_customers = [
        (
            "CUST-DHK-01",
            "Dhaka Retail Mart Ltd.",
            "accounts@dhakaretail.com",
            "+8801711000101",
            "Gulshan-2, Dhaka 1212",
            "001234567-0101",
            "123456789012",
        ),
        (
            "CUST-CTG-02",
            "Chattogram Tech Solutions",
            "finance@ctgtech.com",
            "+8801811000202",
            "Agrabad C/A, Chattogram",
            "009876543-0202",
            "210987654321",
        ),
    ]
    cust_ids: dict[str, uuid.UUID] = {}
    for code, name, email, phone, addr, bin_no, tin_no in demo_customers:
        async with db.transaction(tenant_id) as session:
            existing_c = await CustomerRepository(session, tenant_id).get_by_code(code)
        if existing_c is None:
            created_c = await sales_svc.create_customer(
                tenant_id=tenant_id,
                actor_id=actor_id,
                code=code,
                name=name,
                email=email,
                phone=phone,
                address=addr,
                bin_no=bin_no,
                tin_no=tin_no,
            )
            cust_ids[code] = created_c.id
        else:
            cust_ids[code] = existing_c.id

    async with db.transaction(tenant_id) as session:
        _, inv_count = await SalesInvoiceRepository(session, tenant_id).list_all(offset=0, limit=1)
    if inv_count > 0:
        return

    inv1 = await sales_svc.create_invoice(
        tenant_id=tenant_id,
        actor_id=actor_id,
        customer_id=cust_ids["CUST-DHK-01"],
        invoice_date=date(2026, 11, 5),
        due_date=date(2026, 11, 25),
        notes="ERP Annual License & Deployment",
        lines=[
            InvoiceLineCreateRequest(
                description="Nexzen ERP Enterprise License",
                quantity=Decimal("2"),
                unit_price=Decimal("150000.00"),
                vat_rate_percent=Decimal("15.00"),
            ),
            InvoiceLineCreateRequest(
                description="On-site Staff Training (Dhaka)",
                quantity=Decimal("1"),
                unit_price=Decimal("50000.00"),
                vat_rate_percent=Decimal("15.00"),
            ),
        ],
    )
    await sales_svc.post_invoice(tenant_id=tenant_id, actor_id=actor_id, invoice_id=inv1.id)
    await sales_svc.record_payment(
        tenant_id=tenant_id,
        actor_id=actor_id,
        invoice_id=inv1.id,
        payment_date=date(2026, 11, 12),
        amount=Decimal("250000.00"),
        deposit_account_id=acc_by_code["1120"],
        payment_method="bank",
        reference="BEFTN-2026-1112",
    )

    inv2 = await sales_svc.create_invoice(
        tenant_id=tenant_id,
        actor_id=actor_id,
        customer_id=cust_ids["CUST-CTG-02"],
        invoice_date=date(2026, 11, 15),
        due_date=date(2026, 12, 5),
        notes="POS Hardware & Barcode Printers",
        lines=[
            InvoiceLineCreateRequest(
                description="Thermal Barcode Printer Pro",
                quantity=Decimal("10"),
                unit_price=Decimal("18000.00"),
                vat_rate_percent=Decimal("15.00"),
            )
        ],
    )
    await sales_svc.post_invoice(tenant_id=tenant_id, actor_id=actor_id, invoice_id=inv2.id)


async def _seed_purchase(
    db: Database,
    tenant_id: uuid.UUID,
    actor_id: uuid.UUID,
    acc_by_code: dict[str, uuid.UUID],
) -> None:
    purch_svc = PurchaseService(db)
    demo_suppliers = [
        (
            "SUP-MGN-01",
            "Meghna Wholesale Supplies",
            "billing@meghnasupply.com",
            "+8801712000303",
            "Motijheel C/A, Dhaka",
            "005556667-0103",
            "334455667788",
        ),
        (
            "SUP-GZP-02",
            "Gazipur Industrial Traders",
            "sales@gazipurtraders.com",
            "+8801912000404",
            "Tongi Industrial Area, Gazipur",
            "007778889-0104",
            "445566778899",
        ),
    ]
    sup_ids: dict[str, uuid.UUID] = {}
    for code, name, email, phone, addr, bin_no, tin_no in demo_suppliers:
        async with db.transaction(tenant_id) as session:
            existing_s = await SupplierRepository(session, tenant_id).get_by_code(code)
        if existing_s is None:
            created_s = await purch_svc.create_supplier(
                tenant_id=tenant_id,
                actor_id=actor_id,
                code=code,
                name=name,
                email=email,
                phone=phone,
                address=addr,
                bin_no=bin_no,
                tin_no=tin_no,
            )
            sup_ids[code] = created_s.id
        else:
            sup_ids[code] = existing_s.id

    async with db.transaction(tenant_id) as session:
        _, bill_count = await PurchaseBillRepository(session, tenant_id).list_all(offset=0, limit=1)
    if bill_count > 0:
        return

    bill1 = await purch_svc.create_bill(
        tenant_id=tenant_id,
        actor_id=actor_id,
        supplier_id=sup_ids["SUP-MGN-01"],
        expense_account_id=acc_by_code["5100"],
        bill_date=date(2026, 11, 4),
        due_date=date(2026, 11, 24),
        supplier_bill_ref="MWS-INV-9081",
        tds_rate_percent=Decimal("3.00"),
        vds_rate_percent=Decimal("5.00"),
        notes="Hardware stock procurement",
        lines=[
            PurchaseBillLineCreateRequest(
                description="Thermal Printer Stock Lot",
                quantity=Decimal("15"),
                unit_cost=Decimal("12000.00"),
                vat_rate_percent=Decimal("15.00"),
            )
        ],
    )
    await purch_svc.post_bill(tenant_id=tenant_id, actor_id=actor_id, bill_id=bill1.id)
    await purch_svc.record_payment(
        tenant_id=tenant_id,
        actor_id=actor_id,
        bill_id=bill1.id,
        payment_date=date(2026, 11, 14),
        amount=Decimal("100000.00"),
        payment_account_id=acc_by_code["1120"],
        payment_method="bank",
        reference="CHQ-88201",
    )


async def _seed_inventory(db: Database, tenant_id: uuid.UUID, actor_id: uuid.UUID) -> None:
    inv_svc = InventoryService(db)
    wh_ids: dict[str, uuid.UUID] = {}
    for code, name, loc in (
        ("WH-DHK", "Dhaka Central Warehouse", "Tejgaon Industrial Area, Dhaka"),
        ("WH-CTG", "Chattogram Port Depot", "Halishahar, Chattogram"),
    ):
        async with db.transaction(tenant_id) as session:
            existing_w = await WarehouseRepository(session, tenant_id).get_by_code(code)
        if existing_w is None:
            created_w = await inv_svc.create_warehouse(
                tenant_id=tenant_id, actor_id=actor_id, code=code, name=name, location=loc
            )
            wh_ids[code] = created_w.id
        else:
            wh_ids[code] = existing_w.id

    demo_products = [
        (
            "SKU-PRN-01",
            "Thermal Barcode Printer Pro",
            "pcs",
            Decimal("12000.00"),
            Decimal("18000.00"),
            Decimal("5"),
            Decimal("18"),
        ),
        (
            "SKU-SCN-02",
            "2D Wireless Barcode Scanner",
            "pcs",
            Decimal("4500.00"),
            Decimal("7200.00"),
            Decimal("10"),
            Decimal("25"),
        ),
        (
            "SKU-POS-03",
            "Dual-Screen POS Terminal",
            "pcs",
            Decimal("32000.00"),
            Decimal("45000.00"),
            Decimal("4"),
            Decimal("8"),
        ),
        (
            "SKU-RBN-04",
            "Thermal Wax Ribbon Roll",
            "box",
            Decimal("850.00"),
            Decimal("1350.00"),
            Decimal("15"),
            Decimal("6"),
        ),
    ]
    for sku, name, unit, cost, price, reorder, opening_qty in demo_products:
        async with db.transaction(tenant_id) as session:
            existing_p = await ProductRepository(session, tenant_id).get_by_sku(sku)
        if existing_p is None:
            prod = await inv_svc.create_product(
                tenant_id=tenant_id,
                actor_id=actor_id,
                sku=sku,
                name=name,
                unit=unit,
                unit_cost=cost,
                sale_price=price,
                reorder_level=reorder,
                description="Demo inventory item",
            )
            await inv_svc.record_movement(
                tenant_id=tenant_id,
                actor_id=actor_id,
                movement_date=date(2026, 11, 2),
                movement_type="in",
                product_id=prod.id,
                warehouse_id=wh_ids["WH-DHK"],
                quantity=opening_qty,
                unit_cost=cost,
                reference="OPENING-STOCK-2026",
                notes="Initial warehouse stock",
            )


async def _seed_hr(
    db: Database,
    tenant_id: uuid.UUID,
    actor_id: uuid.UUID,
    acc_by_code: dict[str, uuid.UUID],
) -> None:
    hr_svc = HrService(db)
    demo_employees = [
        (
            "EMP-001",
            "Md. Tariqul Islam",
            "Lead Software Architect",
            "Engineering",
            "tariqul@nexzen.com",
            "+8801711111111",
            "1992269123456",
            "551122334455",
            date(2024, 3, 1),
            Decimal("70000.00"),
            Decimal("35000.00"),
            Decimal("5000.00"),
            Decimal("5000.00"),
            Decimal("10.00"),
            Decimal("5000.00"),
        ),
        (
            "EMP-002",
            "Farhana Akter",
            "Senior Accounts Manager",
            "Finance",
            "farhana@nexzen.com",
            "+8801722222222",
            "1994269654321",
            "662233445566",
            date(2024, 7, 15),
            Decimal("55000.00"),
            Decimal("27500.00"),
            Decimal("4000.00"),
            Decimal("3500.00"),
            Decimal("8.00"),
            Decimal("3000.00"),
        ),
        (
            "EMP-003",
            "Kamrul Hasan",
            "Inventory & Operations Officer",
            "Operations",
            "kamrul@nexzen.com",
            "+8801733333333",
            "1996269777888",
            "773344556677",
            date(2025, 1, 10),
            Decimal("35000.00"),
            Decimal("17500.00"),
            Decimal("3000.00"),
            Decimal("2500.00"),
            Decimal("5.00"),
            Decimal("1000.00"),
        ),
    ]
    for (
        code,
        name,
        desig,
        dept,
        email,
        phone,
        nid,
        tin,
        jdate,
        basic,
        hra,
        med,
        conv,
        pf,
        tax,
    ) in demo_employees:
        async with db.transaction(tenant_id) as session:
            existing_e = await EmployeeRepository(session, tenant_id).get_by_code(code)
        if existing_e is None:
            await hr_svc.create_employee(
                tenant_id=tenant_id,
                actor_id=actor_id,
                employee_code=code,
                full_name=name,
                designation=desig,
                department=dept,
                email=email,
                phone=phone,
                nid_no=nid,
                tin_no=tin,
                join_date=jdate,
                basic_salary=basic,
                house_rent_allowance=hra,
                medical_allowance=med,
                conveyance_allowance=conv,
                other_allowance=Decimal("0.00"),
                pf_deduction_percent=pf,
                tax_deduction_amount=tax,
            )

    async with db.transaction(tenant_id) as session:
        oct_run = await PayrollRunRepository(session, tenant_id).get_by_period(2026, 10)
    if oct_run is None:
        with contextlib.suppress(ConflictError):
            run_oct, _ = await hr_svc.create_payroll_run(
                tenant_id=tenant_id,
                actor_id=actor_id,
                pay_year=2026,
                pay_month=10,
                notes="October 2026 Staff Salary",
            )
            await hr_svc.post_payroll_run(
                tenant_id=tenant_id,
                actor_id=actor_id,
                run_id=run_oct.id,
                salary_expense_account_id=acc_by_code["5200"],
                payment_account_id=acc_by_code["1120"],
                deductions_payable_account_id=acc_by_code["2210"],
            )

    async with db.transaction(tenant_id) as session:
        nov_run = await PayrollRunRepository(session, tenant_id).get_by_period(2026, 11)
    if nov_run is None:
        with contextlib.suppress(ConflictError):
            await hr_svc.create_payroll_run(
                tenant_id=tenant_id,
                actor_id=actor_id,
                pay_year=2026,
                pay_month=11,
                notes="November 2026 Staff Salary (Draft — ready to Post to GL)",
            )


async def seed_demo_data() -> None:
    settings = get_settings()
    tenant_code = os.getenv("SEED_TENANT_CODE", "nexzen-demo").strip().lower()
    admin_email = os.getenv("SEED_ADMIN_EMAIL", "admin@nexzen.com").strip().lower()

    db = Database(settings)
    try:
        async with db.transaction(None) as session:
            await session.execute(
                text("SELECT set_config('app.lookup_tenant_code', :code, true)"),
                {"code": tenant_code},
            )
            found_tid = (
                await session.execute(select(Tenant.id).where(Tenant.code == tenant_code))
            ).scalar_one_or_none()
            if found_tid is None:
                raise RuntimeError(
                    f"Tenant '{tenant_code}' not found. Run `python -m app.seed` first."
                )
            tenant_id = found_tid

        async with db.transaction(tenant_id) as session:
            admin = await UserRepository(session, tenant_id).get_by_email(admin_email)
            if admin is None:
                raise RuntimeError(f"Admin user '{admin_email}' not found.")
            actor_id = admin.id

        await _ensure_auditor_user(db, tenant_id, actor_id)
        acc_by_code = await _seed_accounting(db, tenant_id, actor_id)
        await _seed_vat(db, tenant_id, actor_id)
        await _seed_sales(db, tenant_id, actor_id, acc_by_code)
        await _seed_purchase(db, tenant_id, actor_id, acc_by_code)
        await _seed_inventory(db, tenant_id, actor_id)
        await _seed_hr(db, tenant_id, actor_id, acc_by_code)

        sys.stdout.write(
            f"[nexzen] Demo business data seeded successfully for tenant '{tenant_code}'.\n"
        )
    finally:
        await db.dispose()


if __name__ == "__main__":
    asyncio.run(seed_demo_data())
