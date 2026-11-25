"""Sales & Invoicing service with atomic General Ledger (GL) double-entry integration."""

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
from app.models.sales import Customer, CustomerPayment, SalesInvoice, SalesInvoiceLine
from app.repositories.accounting import AccountRepository, JournalEntryRepository
from app.repositories.sales import (
    CustomerPaymentRepository,
    CustomerRepository,
    SalesInvoiceRepository,
)
from app.schemas.sales import InvoiceLineCreateRequest, PaymentMethod
from app.services.audit_service import record_audit

ZERO = Decimal("0.00")
HUNDRED = Decimal("100")
TWO_PLACES = Decimal("0.01")

# Standard COA codes used for automated GL posting (seeded via Accounting COA).
AR_ACCOUNT_CODE = "1200"
SALES_REVENUE_CODE = "4100"
VAT_OUTPUT_CODE = "2200"


@dataclass(frozen=True, slots=True)
class ComputedInvoiceLine:
    description: str
    quantity: Decimal
    unit_price: Decimal
    vat_rate_percent: Decimal
    line_subtotal: Decimal
    line_vat: Decimal
    line_total: Decimal


def compute_line_totals(line: InvoiceLineCreateRequest) -> ComputedInvoiceLine:
    """Compute exact Decimal subtotal, configurable VAT, and total using ROUND_HALF_UP."""
    subtotal = (line.quantity * line.unit_price).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    vat = (subtotal * line.vat_rate_percent / HUNDRED).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    total = (subtotal + vat).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    return ComputedInvoiceLine(
        description=line.description.strip(),
        quantity=line.quantity,
        unit_price=line.unit_price,
        vat_rate_percent=line.vat_rate_percent,
        line_subtotal=subtotal,
        line_vat=vat,
        line_total=total,
    )


class SalesService:
    """All Sales & Invoicing business rules live here."""

    def __init__(self, database: Database) -> None:
        self._database = database

    async def list_customers(
        self,
        *,
        tenant_id: uuid.UUID,
        pagination: PaginationParams,
        sort: SortParams,
        search: str | None = None,
    ) -> tuple[list[Customer], int]:
        order_by = build_order_by(
            sort,
            allowed={
                "code": Customer.code,
                "name": Customer.name,
                "created_at": Customer.created_at,
            },
            default=[Customer.name.asc()],
        )
        filters = build_filters([FilterRule(column=Customer.name, operator="ilike", value=search)])
        async with self._database.transaction(tenant_id) as session:
            return await CustomerRepository(session, tenant_id).list_all(
                offset=pagination.offset,
                limit=pagination.limit,
                filters=filters,
                order_by=order_by,
            )

    async def create_customer(
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
    ) -> Customer:
        cleaned_code = code.strip().upper()
        async with self._database.transaction(tenant_id) as session:
            repo = CustomerRepository(session, tenant_id)
            if await repo.get_by_code(cleaned_code) is not None:
                raise ConflictError("A customer with this code already exists.")

            customer = await repo.create(
                Customer(
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
                action="sales.customer.created",
                resource_type="customer",
                resource_id=customer.id,
                after_data={
                    "code": customer.code,
                    "name": customer.name,
                    "bin_no": customer.bin_no,
                },
            )
            return customer

    async def list_invoices(
        self,
        *,
        tenant_id: uuid.UUID,
        pagination: PaginationParams,
        sort: SortParams,
        status_filter: str | None = None,
        customer_id: uuid.UUID | None = None,
    ) -> tuple[list[SalesInvoice], int]:
        order_by = build_order_by(
            sort,
            allowed={
                "invoice_date": SalesInvoice.invoice_date,
                "invoice_no": SalesInvoice.invoice_no,
                "grand_total": SalesInvoice.grand_total,
                "created_at": SalesInvoice.created_at,
            },
            default=[SalesInvoice.invoice_date.desc(), SalesInvoice.created_at.desc()],
        )
        filters = build_filters(
            [
                FilterRule(column=SalesInvoice.status, operator="eq", value=status_filter),
                FilterRule(column=SalesInvoice.customer_id, operator="eq", value=customer_id),
            ]
        )
        async with self._database.transaction(tenant_id) as session:
            return await SalesInvoiceRepository(session, tenant_id).list_all(
                offset=pagination.offset,
                limit=pagination.limit,
                filters=filters,
                order_by=order_by,
            )

    async def create_invoice(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        customer_id: uuid.UUID,
        invoice_date: date,
        due_date: date,
        notes: str,
        lines: Sequence[InvoiceLineCreateRequest],
    ) -> SalesInvoice:
        computed = [compute_line_totals(line) for line in lines]
        subtotal = sum((item.line_subtotal for item in computed), ZERO)
        vat_total = sum((item.line_vat for item in computed), ZERO)
        grand_total = sum((item.line_total for item in computed), ZERO)
        if grand_total <= ZERO:
            raise BusinessRuleError("Invoice grand total must be greater than zero.")

        async with self._database.transaction(tenant_id) as session:
            customer = await CustomerRepository(session, tenant_id).get_by_id(customer_id)
            if customer is None or not customer.is_active:
                raise NotFoundError("Customer not found or inactive.")

            inv_repo = SalesInvoiceRepository(session, tenant_id)
            seq = await inv_repo.next_invoice_sequence(invoice_date.year)
            invoice_no = f"INV-{invoice_date.year}-{seq:06d}"

            invoice = await inv_repo.create(
                SalesInvoice(
                    tenant_id=tenant_id,
                    invoice_no=invoice_no,
                    customer_id=customer_id,
                    invoice_date=invoice_date,
                    due_date=due_date,
                    status="draft",
                    subtotal=subtotal,
                    vat_total=vat_total,
                    grand_total=grand_total,
                    paid_amount=ZERO,
                    notes=notes.strip(),
                ),
                actor_id=actor_id,
            )
            for idx, item in enumerate(computed, start=1):
                session.add(
                    SalesInvoiceLine(
                        tenant_id=tenant_id,
                        invoice_id=invoice.id,
                        line_no=idx,
                        description=item.description,
                        quantity=item.quantity,
                        unit_price=item.unit_price,
                        vat_rate_percent=item.vat_rate_percent,
                        line_subtotal=item.line_subtotal,
                        line_vat=item.line_vat,
                        line_total=item.line_total,
                        created_by=actor_id,
                        updated_by=actor_id,
                    )
                )
            await session.flush()
            loaded = await inv_repo.get_with_lines(invoice.id)
            if loaded is None:
                raise NotFoundError("Invoice not found after creation.")

            await record_audit(
                session,
                tenant_id=tenant_id,
                actor_id=actor_id,
                action="sales.invoice.created",
                resource_type="sales_invoice",
                resource_id=loaded.id,
                after_data={
                    "invoice_no": loaded.invoice_no,
                    "customer_id": customer_id,
                    "subtotal": subtotal,
                    "vat_total": vat_total,
                    "grand_total": grand_total,
                },
            )
            return loaded

    async def post_invoice(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        invoice_id: uuid.UUID,
    ) -> SalesInvoice:
        """Confirm draft invoice and atomically post double-entry GL journal."""
        async with self._database.transaction(tenant_id) as session:
            inv_repo = SalesInvoiceRepository(session, tenant_id)
            acc_repo = AccountRepository(session, tenant_id)
            je_repo = JournalEntryRepository(session, tenant_id)

            invoice = await inv_repo.get_with_lines(invoice_id)
            if invoice is None:
                raise NotFoundError("Sales invoice not found.")
            if invoice.status != "draft":
                raise BusinessRuleError("Only draft invoices can be posted.")

            ar_acc = await acc_repo.get_by_code(AR_ACCOUNT_CODE)
            sales_acc = await acc_repo.get_by_code(SALES_REVENUE_CODE)
            vat_acc = (
                await acc_repo.get_by_code(VAT_OUTPUT_CODE) if invoice.vat_total > ZERO else None
            )
            if (
                ar_acc is None
                or sales_acc is None
                or (invoice.vat_total > ZERO and vat_acc is None)
            ):
                raise BusinessRuleError(
                    "Required GL accounts (1200 AR, 4100 Sales, 2200 VAT Output) are missing. "
                    "Seed the Chart of Accounts first."
                )

            now = datetime.now(UTC)
            seq = await je_repo.next_voucher_sequence(invoice.invoice_date.year)
            voucher_no = f"JV-{invoice.invoice_date.year}-{seq:06d}"

            entry = await je_repo.create(
                JournalEntry(
                    tenant_id=tenant_id,
                    voucher_no=voucher_no,
                    entry_date=invoice.invoice_date,
                    reference=invoice.invoice_no,
                    narration=f"Sales Invoice {invoice.invoice_no}",
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
                    account_id=ar_acc.id,
                    line_no=1,
                    description=f"Accounts Receivable — {invoice.invoice_no}",
                    debit=invoice.grand_total,
                    credit=ZERO,
                    created_by=actor_id,
                    updated_by=actor_id,
                )
            )
            session.add(
                JournalLine(
                    tenant_id=tenant_id,
                    journal_entry_id=entry.id,
                    account_id=sales_acc.id,
                    line_no=2,
                    description=f"Sales Revenue — {invoice.invoice_no}",
                    debit=ZERO,
                    credit=invoice.subtotal,
                    created_by=actor_id,
                    updated_by=actor_id,
                )
            )
            if invoice.vat_total > ZERO and vat_acc is not None:
                session.add(
                    JournalLine(
                        tenant_id=tenant_id,
                        journal_entry_id=entry.id,
                        account_id=vat_acc.id,
                        line_no=3,
                        description=f"VAT Output Payable — {invoice.invoice_no}",
                        debit=ZERO,
                        credit=invoice.vat_total,
                        created_by=actor_id,
                        updated_by=actor_id,
                    )
                )

            invoice.status = "posted"
            invoice.journal_entry_id = entry.id
            await inv_repo.update(invoice, actor_id=actor_id)
            await session.flush()

            await record_audit(
                session,
                tenant_id=tenant_id,
                actor_id=actor_id,
                action="sales.invoice.posted",
                resource_type="sales_invoice",
                resource_id=invoice.id,
                before_data={"status": "draft"},
                after_data={
                    "status": "posted",
                    "journal_entry_id": entry.id,
                    "voucher_no": voucher_no,
                    "grand_total": invoice.grand_total,
                },
            )
            loaded = await inv_repo.get_with_lines(invoice.id)
            if loaded is None:
                raise NotFoundError("Sales invoice not found.")
            return loaded

    async def record_payment(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        invoice_id: uuid.UUID,
        payment_date: date,
        amount: Decimal,
        payment_method: PaymentMethod,
        deposit_account_id: uuid.UUID,
        reference: str,
    ) -> CustomerPayment:
        """Record a customer receipt and atomically post DR Cash/Bank, CR AR."""
        async with self._database.transaction(tenant_id) as session:
            inv_repo = SalesInvoiceRepository(session, tenant_id)
            pay_repo = CustomerPaymentRepository(session, tenant_id)
            acc_repo = AccountRepository(session, tenant_id)
            je_repo = JournalEntryRepository(session, tenant_id)

            invoice = await inv_repo.get_by_id(invoice_id)
            if invoice is None:
                raise NotFoundError("Sales invoice not found.")
            if invoice.status not in {"posted", "partially_paid"}:
                raise BusinessRuleError("Payments can only be recorded on posted invoices.")

            remaining = invoice.grand_total - invoice.paid_amount
            if amount > remaining:
                raise BusinessRuleError(
                    "Payment amount exceeds remaining invoice balance.",
                    details={"remaining_balance": str(remaining), "attempted": str(amount)},
                )

            deposit_acc = await acc_repo.get_by_id(deposit_account_id)
            if deposit_acc is None or not deposit_acc.is_active or deposit_acc.is_group:
                raise BusinessRuleError("Invalid or inactive deposit ledger account.")

            ar_acc = await acc_repo.get_by_code(AR_ACCOUNT_CODE)
            if ar_acc is None:
                raise BusinessRuleError("Accounts Receivable (1200) account is missing.")

            now = datetime.now(UTC)
            je_seq = await je_repo.next_voucher_sequence(payment_date.year)
            voucher_no = f"JV-{payment_date.year}-{je_seq:06d}"

            entry = await je_repo.create(
                JournalEntry(
                    tenant_id=tenant_id,
                    voucher_no=voucher_no,
                    entry_date=payment_date,
                    reference=invoice.invoice_no,
                    narration=f"Payment received for {invoice.invoice_no}",
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
                    account_id=deposit_acc.id,
                    line_no=1,
                    description=f"Receipt ({payment_method}) — {invoice.invoice_no}",
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
                    account_id=ar_acc.id,
                    line_no=2,
                    description=f"Clear AR — {invoice.invoice_no}",
                    debit=ZERO,
                    credit=amount,
                    created_by=actor_id,
                    updated_by=actor_id,
                )
            )

            pay_seq = await pay_repo.next_payment_sequence(payment_date.year)
            payment_no = f"RCPT-{payment_date.year}-{pay_seq:06d}"
            payment = await pay_repo.create(
                CustomerPayment(
                    tenant_id=tenant_id,
                    payment_no=payment_no,
                    invoice_id=invoice.id,
                    customer_id=invoice.customer_id,
                    payment_date=payment_date,
                    amount=amount,
                    payment_method=payment_method,
                    deposit_account_id=deposit_acc.id,
                    reference=reference.strip(),
                    journal_entry_id=entry.id,
                ),
                actor_id=actor_id,
            )

            prev_status = invoice.status
            invoice.paid_amount = invoice.paid_amount + amount
            invoice.status = (
                "paid" if invoice.paid_amount == invoice.grand_total else "partially_paid"
            )
            await inv_repo.update(invoice, actor_id=actor_id)
            await session.flush()

            await record_audit(
                session,
                tenant_id=tenant_id,
                actor_id=actor_id,
                action="sales.payment.recorded",
                resource_type="customer_payment",
                resource_id=payment.id,
                before_data={"invoice_status": prev_status},
                after_data={
                    "payment_no": payment.payment_no,
                    "invoice_no": invoice.invoice_no,
                    "amount": amount,
                    "new_invoice_status": invoice.status,
                    "journal_entry_id": entry.id,
                },
            )
            return payment
