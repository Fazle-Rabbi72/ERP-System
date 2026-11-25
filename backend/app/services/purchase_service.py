"""Purchase & Supplier service with configurable VAT, TDS, VDS and atomic GL posting."""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal

from app.core.db import Database
from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.core.query import (
    FilterRule,
    PaginationParams,
    SortParams,
    build_filters,
    build_order_by,
)
from app.models.accounting import JournalEntry, JournalLine
from app.models.purchase import PurchaseBill, PurchaseBillLine, Supplier, SupplierPayment
from app.repositories.accounting import AccountRepository, JournalEntryRepository
from app.repositories.purchase import (
    PurchaseBillRepository,
    SupplierPaymentRepository,
    SupplierRepository,
)
from app.schemas.purchase import PaymentMethod, PurchaseBillLineCreateRequest
from app.services.audit_service import record_audit

ZERO = Decimal("0.00")
HUNDRED = Decimal("100")
TWO_PLACES = Decimal("0.01")

VAT_INPUT_CODE = "1400"
AP_ACCOUNT_CODE = "2100"
TDS_VDS_PAYABLE_CODE = "2210"


@dataclass(frozen=True, slots=True)
class ComputedBillLine:
    description: str
    quantity: Decimal
    unit_cost: Decimal
    vat_rate_percent: Decimal
    line_subtotal: Decimal
    line_vat: Decimal
    line_total: Decimal


@dataclass(frozen=True, slots=True)
class ComputedBillTotals:
    lines: list[ComputedBillLine]
    subtotal: Decimal
    vat_total: Decimal
    gross_total: Decimal
    tds_amount: Decimal
    vds_amount: Decimal
    net_payable: Decimal


def compute_bill_totals(
    lines: Sequence[PurchaseBillLineCreateRequest],
    *,
    tds_rate_percent: Decimal,
    vds_rate_percent: Decimal,
) -> ComputedBillTotals:
    """Compute exact Decimal totals including configurable VAT, TDS & VDS."""
    computed_lines: list[ComputedBillLine] = []
    for line in lines:
        sub = (line.quantity * line.unit_cost).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        vat = (sub * line.vat_rate_percent / HUNDRED).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
        computed_lines.append(
            ComputedBillLine(
                description=line.description.strip(),
                quantity=line.quantity,
                unit_cost=line.unit_cost,
                vat_rate_percent=line.vat_rate_percent,
                line_subtotal=sub,
                line_vat=vat,
                line_total=(sub + vat).quantize(TWO_PLACES, rounding=ROUND_HALF_UP),
            )
        )
    subtotal = sum((item.line_subtotal for item in computed_lines), ZERO)
    vat_total = sum((item.line_vat for item in computed_lines), ZERO)
    gross_total = subtotal + vat_total
    tds_amount = (subtotal * tds_rate_percent / HUNDRED).quantize(
        TWO_PLACES, rounding=ROUND_HALF_UP
    )
    vds_amount = (subtotal * vds_rate_percent / HUNDRED).quantize(
        TWO_PLACES, rounding=ROUND_HALF_UP
    )
    net_payable = gross_total - tds_amount - vds_amount
    if gross_total <= ZERO or net_payable <= ZERO:
        raise BusinessRuleError("Bill gross total and net payable must be greater than zero.")
    return ComputedBillTotals(
        lines=computed_lines,
        subtotal=subtotal,
        vat_total=vat_total,
        gross_total=gross_total,
        tds_amount=tds_amount,
        vds_amount=vds_amount,
        net_payable=net_payable,
    )


class PurchaseService:
    """All Purchase & Supplier business logic lives here."""

    def __init__(self, database: Database) -> None:
        self._database = database

    async def list_suppliers(
        self,
        *,
        tenant_id: uuid.UUID,
        pagination: PaginationParams,
        sort: SortParams,
        search: str | None = None,
    ) -> tuple[list[Supplier], int]:
        order_by = build_order_by(
            sort,
            allowed={
                "code": Supplier.code,
                "name": Supplier.name,
                "created_at": Supplier.created_at,
            },
            default=[Supplier.name.asc()],
        )
        filters = build_filters([FilterRule(column=Supplier.name, operator="ilike", value=search)])
        async with self._database.transaction(tenant_id) as session:
            return await SupplierRepository(session, tenant_id).list_all(
                offset=pagination.offset,
                limit=pagination.limit,
                filters=filters,
                order_by=order_by,
            )

    async def create_supplier(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        code: str,
        name: str,
        phone: str,
        email: str,
        address: str,
        bin_no: str,
        tin_no: str,
    ) -> Supplier:
        cleaned_code = code.strip().upper()
        async with self._database.transaction(tenant_id) as session:
            repo = SupplierRepository(session, tenant_id)
            if await repo.get_by_code(cleaned_code) is not None:
                raise ConflictError("A supplier with this code already exists.")

            supplier = await repo.create(
                Supplier(
                    tenant_id=tenant_id,
                    code=cleaned_code,
                    name=name.strip(),
                    phone=phone.strip(),
                    email=email.strip().lower(),
                    address=address.strip(),
                    bin_no=bin_no.strip(),
                    tin_no=tin_no.strip(),
                ),
                actor_id=actor_id,
            )
            await record_audit(
                session,
                tenant_id=tenant_id,
                actor_id=actor_id,
                action="purchase.supplier.created",
                resource_type="supplier",
                resource_id=supplier.id,
                after_data={
                    "code": supplier.code,
                    "name": supplier.name,
                    "bin_no": supplier.bin_no,
                },
            )
            return supplier

    async def list_bills(
        self,
        *,
        tenant_id: uuid.UUID,
        pagination: PaginationParams,
        sort: SortParams,
        status_filter: str | None = None,
        supplier_id: uuid.UUID | None = None,
    ) -> tuple[list[PurchaseBill], int]:
        order_by = build_order_by(
            sort,
            allowed={
                "bill_date": PurchaseBill.bill_date,
                "bill_no": PurchaseBill.bill_no,
                "net_payable": PurchaseBill.net_payable,
                "created_at": PurchaseBill.created_at,
            },
            default=[PurchaseBill.bill_date.desc(), PurchaseBill.created_at.desc()],
        )
        filters = build_filters(
            [
                FilterRule(column=PurchaseBill.status, operator="eq", value=status_filter),
                FilterRule(column=PurchaseBill.supplier_id, operator="eq", value=supplier_id),
            ]
        )
        async with self._database.transaction(tenant_id) as session:
            return await PurchaseBillRepository(session, tenant_id).list_all(
                offset=pagination.offset,
                limit=pagination.limit,
                filters=filters,
                order_by=order_by,
            )

    async def create_bill(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        supplier_id: uuid.UUID,
        expense_account_id: uuid.UUID,
        supplier_bill_ref: str,
        bill_date: date,
        due_date: date,
        tds_rate_percent: Decimal,
        vds_rate_percent: Decimal,
        notes: str,
        lines: Sequence[PurchaseBillLineCreateRequest],
    ) -> PurchaseBill:
        totals = compute_bill_totals(
            lines,
            tds_rate_percent=tds_rate_percent,
            vds_rate_percent=vds_rate_percent,
        )

        async with self._database.transaction(tenant_id) as session:
            supplier = await SupplierRepository(session, tenant_id).get_by_id(supplier_id)
            if supplier is None or not supplier.is_active:
                raise NotFoundError("Supplier not found or inactive.")

            exp_acc = await AccountRepository(session, tenant_id).get_by_id(expense_account_id)
            if exp_acc is None or not exp_acc.is_active or exp_acc.is_group:
                raise BusinessRuleError("Invalid or inactive expense/inventory ledger account.")

            bill_repo = PurchaseBillRepository(session, tenant_id)
            seq = await bill_repo.next_bill_sequence(bill_date.year)
            bill_no = f"BILL-{bill_date.year}-{seq:06d}"

            bill = await bill_repo.create(
                PurchaseBill(
                    tenant_id=tenant_id,
                    bill_no=bill_no,
                    supplier_bill_ref=supplier_bill_ref.strip(),
                    supplier_id=supplier_id,
                    expense_account_id=expense_account_id,
                    bill_date=bill_date,
                    due_date=due_date,
                    status="draft",
                    subtotal=totals.subtotal,
                    vat_total=totals.vat_total,
                    gross_total=totals.gross_total,
                    tds_rate_percent=tds_rate_percent,
                    tds_amount=totals.tds_amount,
                    vds_rate_percent=vds_rate_percent,
                    vds_amount=totals.vds_amount,
                    net_payable=totals.net_payable,
                    paid_amount=ZERO,
                    notes=notes.strip(),
                ),
                actor_id=actor_id,
            )
            for idx, item in enumerate(totals.lines, start=1):
                session.add(
                    PurchaseBillLine(
                        tenant_id=tenant_id,
                        bill_id=bill.id,
                        line_no=idx,
                        description=item.description,
                        quantity=item.quantity,
                        unit_cost=item.unit_cost,
                        vat_rate_percent=item.vat_rate_percent,
                        line_subtotal=item.line_subtotal,
                        line_vat=item.line_vat,
                        line_total=item.line_total,
                        created_by=actor_id,
                        updated_by=actor_id,
                    )
                )
            await session.flush()
            loaded = await bill_repo.get_with_lines(bill.id)
            if loaded is None:
                raise NotFoundError("Purchase bill not found after creation.")

            await record_audit(
                session,
                tenant_id=tenant_id,
                actor_id=actor_id,
                action="purchase.bill.created",
                resource_type="purchase_bill",
                resource_id=loaded.id,
                after_data={
                    "bill_no": loaded.bill_no,
                    "gross_total": totals.gross_total,
                    "tds_amount": totals.tds_amount,
                    "vds_amount": totals.vds_amount,
                    "net_payable": totals.net_payable,
                },
            )
            return loaded

    async def post_bill(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        bill_id: uuid.UUID,
    ) -> PurchaseBill:
        """Post draft purchase bill and atomically create balanced GL journal."""
        async with self._database.transaction(tenant_id) as session:
            bill_repo = PurchaseBillRepository(session, tenant_id)
            acc_repo = AccountRepository(session, tenant_id)
            je_repo = JournalEntryRepository(session, tenant_id)

            bill = await bill_repo.get_with_lines(bill_id)
            if bill is None:
                raise NotFoundError("Purchase bill not found.")
            if bill.status != "draft":
                raise BusinessRuleError("Only draft purchase bills can be posted.")

            ap_acc = await acc_repo.get_by_code(AP_ACCOUNT_CODE)
            vat_in_acc = (
                await acc_repo.get_by_code(VAT_INPUT_CODE) if bill.vat_total > ZERO else None
            )
            withholding_total = bill.tds_amount + bill.vds_amount
            wh_acc = (
                await acc_repo.get_by_code(TDS_VDS_PAYABLE_CODE)
                if withholding_total > ZERO
                else None
            )
            if (
                ap_acc is None
                or (bill.vat_total > ZERO and vat_in_acc is None)
                or (withholding_total > ZERO and wh_acc is None)
            ):
                raise BusinessRuleError(
                    "Required GL accounts (2100 AP, 1400 VAT Input, 2210 TDS/VDS Payable) "
                    "are missing. Seed the Chart of Accounts first."
                )

            now = datetime.now(UTC)
            seq = await je_repo.next_voucher_sequence(bill.bill_date.year)
            voucher_no = f"JV-{bill.bill_date.year}-{seq:06d}"

            entry = await je_repo.create(
                JournalEntry(
                    tenant_id=tenant_id,
                    voucher_no=voucher_no,
                    entry_date=bill.bill_date,
                    reference=bill.bill_no,
                    narration=f"Purchase Bill {bill.bill_no}",
                    status="posted",
                    posted_at=now,
                    posted_by=actor_id,
                ),
                actor_id=actor_id,
            )

            line_no = 1
            session.add(
                JournalLine(
                    tenant_id=tenant_id,
                    journal_entry_id=entry.id,
                    account_id=bill.expense_account_id,
                    line_no=line_no,
                    description=f"Purchase Expense/Inventory — {bill.bill_no}",
                    debit=bill.subtotal,
                    credit=ZERO,
                    created_by=actor_id,
                    updated_by=actor_id,
                )
            )
            if bill.vat_total > ZERO and vat_in_acc is not None:
                line_no += 1
                session.add(
                    JournalLine(
                        tenant_id=tenant_id,
                        journal_entry_id=entry.id,
                        account_id=vat_in_acc.id,
                        line_no=line_no,
                        description=f"VAT Input Receivable — {bill.bill_no}",
                        debit=bill.vat_total,
                        credit=ZERO,
                        created_by=actor_id,
                        updated_by=actor_id,
                    )
                )

            line_no += 1
            session.add(
                JournalLine(
                    tenant_id=tenant_id,
                    journal_entry_id=entry.id,
                    account_id=ap_acc.id,
                    line_no=line_no,
                    description=f"Accounts Payable — {bill.bill_no}",
                    debit=ZERO,
                    credit=bill.net_payable,
                    created_by=actor_id,
                    updated_by=actor_id,
                )
            )
            if withholding_total > ZERO and wh_acc is not None:
                line_no += 1
                session.add(
                    JournalLine(
                        tenant_id=tenant_id,
                        journal_entry_id=entry.id,
                        account_id=wh_acc.id,
                        line_no=line_no,
                        description=f"TDS/VDS Withholding Payable — {bill.bill_no}",
                        debit=ZERO,
                        credit=withholding_total,
                        created_by=actor_id,
                        updated_by=actor_id,
                    )
                )

            bill.status = "posted"
            bill.journal_entry_id = entry.id
            await bill_repo.update(bill, actor_id=actor_id)
            await session.flush()

            await record_audit(
                session,
                tenant_id=tenant_id,
                actor_id=actor_id,
                action="purchase.bill.posted",
                resource_type="purchase_bill",
                resource_id=bill.id,
                before_data={"status": "draft"},
                after_data={
                    "status": "posted",
                    "voucher_no": voucher_no,
                    "net_payable": bill.net_payable,
                    "withholding_total": withholding_total,
                },
            )
            loaded = await bill_repo.get_with_lines(bill.id)
            if loaded is None:
                raise NotFoundError("Purchase bill not found.")
            return loaded

    async def record_payment(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        bill_id: uuid.UUID,
        payment_date: date,
        amount: Decimal,
        payment_method: PaymentMethod,
        payment_account_id: uuid.UUID,
        reference: str,
    ) -> SupplierPayment:
        """Record supplier payment and atomically post DR AP (2100), CR Cash/Bank."""
        async with self._database.transaction(tenant_id) as session:
            bill_repo = PurchaseBillRepository(session, tenant_id)
            pay_repo = SupplierPaymentRepository(session, tenant_id)
            acc_repo = AccountRepository(session, tenant_id)
            je_repo = JournalEntryRepository(session, tenant_id)

            bill = await bill_repo.get_by_id(bill_id)
            if bill is None:
                raise NotFoundError("Purchase bill not found.")
            if bill.status not in {"posted", "partially_paid"}:
                raise BusinessRuleError("Payments can only be recorded on posted bills.")

            remaining = bill.net_payable - bill.paid_amount
            if amount > remaining:
                raise BusinessRuleError(
                    "Payment amount exceeds remaining net payable balance.",
                    details={"remaining_balance": str(remaining), "attempted": str(amount)},
                )

            pay_acc = await acc_repo.get_by_id(payment_account_id)
            if pay_acc is None or not pay_acc.is_active or pay_acc.is_group:
                raise BusinessRuleError("Invalid or inactive payment ledger account.")

            ap_acc = await acc_repo.get_by_code(AP_ACCOUNT_CODE)
            if ap_acc is None:
                raise BusinessRuleError("Accounts Payable (2100) account is missing.")

            now = datetime.now(UTC)
            je_seq = await je_repo.next_voucher_sequence(payment_date.year)
            voucher_no = f"JV-{payment_date.year}-{je_seq:06d}"

            entry = await je_repo.create(
                JournalEntry(
                    tenant_id=tenant_id,
                    voucher_no=voucher_no,
                    entry_date=payment_date,
                    reference=bill.bill_no,
                    narration=f"Supplier payment for {bill.bill_no}",
                    status="posted",
                    posted_at=now,
                    posted_by=actor_id,
                ),
                actor_id=actor_id,
            )
            session.add(
                JournalLine(
                    tenant_id=tenant_id,
                    journal_entry_id=entry.id,
                    account_id=ap_acc.id,
                    line_no=1,
                    description=f"Clear AP — {bill.bill_no}",
                    debit=amount,
                    credit=ZERO,
                    created_by=actor_id,
                    updated_by=actor_id,
                )
            )
            session.add(
                JournalLine(
                    tenant_id=tenant_id,
                    journal_entry_id=entry.id,
                    account_id=pay_acc.id,
                    line_no=2,
                    description=f"Disbursement ({payment_method}) — {bill.bill_no}",
                    debit=ZERO,
                    credit=amount,
                    created_by=actor_id,
                    updated_by=actor_id,
                )
            )

            pay_seq = await pay_repo.next_payment_sequence(payment_date.year)
            payment_no = f"PAY-{payment_date.year}-{pay_seq:06d}"
            payment = await pay_repo.create(
                SupplierPayment(
                    tenant_id=tenant_id,
                    payment_no=payment_no,
                    bill_id=bill.id,
                    supplier_id=bill.supplier_id,
                    payment_date=payment_date,
                    amount=amount,
                    payment_method=payment_method,
                    payment_account_id=pay_acc.id,
                    reference=reference.strip(),
                    journal_entry_id=entry.id,
                ),
                actor_id=actor_id,
            )

            prev_status = bill.status
            bill.paid_amount = bill.paid_amount + amount
            bill.status = "paid" if bill.paid_amount == bill.net_payable else "partially_paid"
            await bill_repo.update(bill, actor_id=actor_id)
            await session.flush()

            await record_audit(
                session,
                tenant_id=tenant_id,
                actor_id=actor_id,
                action="purchase.payment.recorded",
                resource_type="supplier_payment",
                resource_id=payment.id,
                before_data={"bill_status": prev_status},
                after_data={
                    "payment_no": payment.payment_no,
                    "bill_no": bill.bill_no,
                    "amount": amount,
                    "new_bill_status": bill.status,
                },
            )
            return payment
