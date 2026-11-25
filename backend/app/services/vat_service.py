"""Bangladesh VAT & Mushak service (configurable rates + Mushak 6.1, 6.2, 6.3, 9.1)."""

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.core.db import Database
from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.core.query import (
    FilterRule,
    PaginationParams,
    SortParams,
    build_filters,
    build_order_by,
)
from app.models.vat import VatRate
from app.repositories.sales import CustomerRepository, SalesInvoiceRepository
from app.repositories.tenant import TenantRepository
from app.repositories.vat import (
    POSTED_STATUSES,
    Mushak61Row,
    Mushak62Row,
    MushakReportRepository,
    VatRateRepository,
)
from app.services.audit_service import record_audit

ZERO = Decimal("0.00")

MUSHAK_91_ADVISORY = (
    "Working summary computed from posted Sales Invoices and Purchase Bills. "
    "Verify input VAT rebate eligibility, VDS/TDS adjustments, and current NBR SRO rules "
    "with your VAT consultant before official Mushak 9.1 filing."
)


def compute_net_vat_position(output_vat: Decimal, input_vat: Decimal) -> tuple[Decimal, Decimal]:
    """Return `(net_vat_payable, carry_forward_credit)` in exact Decimal."""
    diff = output_vat - input_vat
    if diff >= ZERO:
        return diff, ZERO
    return ZERO, -diff


@dataclass(frozen=True, slots=True)
class Mushak63Data:
    invoice_id: uuid.UUID
    invoice_no: str
    invoice_date: date
    seller_name: str
    customer_name: str
    customer_bin: str
    customer_address: str
    lines: list[tuple[int, str, Decimal, Decimal, Decimal, Decimal, Decimal, Decimal]]
    subtotal: Decimal
    vat_total: Decimal
    grand_total: Decimal


class VatService:
    """All configurable VAT & Mushak reporting logic lives here."""

    def __init__(self, database: Database) -> None:
        self._database = database

    async def list_rates(
        self,
        *,
        tenant_id: uuid.UUID,
        pagination: PaginationParams,
        sort: SortParams,
        search: str | None = None,
    ) -> tuple[list[VatRate], int]:
        order_by = build_order_by(
            sort,
            allowed={"code": VatRate.code, "rate_percent": VatRate.rate_percent},
            default=[VatRate.code.asc()],
        )
        filters = build_filters([FilterRule(column=VatRate.name, operator="ilike", value=search)])
        async with self._database.transaction(tenant_id) as session:
            return await VatRateRepository(session, tenant_id).list_all(
                offset=pagination.offset,
                limit=pagination.limit,
                filters=filters,
                order_by=order_by,
            )

    async def create_rate(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        code: str,
        name: str,
        rate_percent: Decimal,
        is_vds_applicable: bool,
        statutory_note: str,
    ) -> VatRate:
        cleaned_code = code.strip().upper()
        async with self._database.transaction(tenant_id) as session:
            repo = VatRateRepository(session, tenant_id)
            if await repo.get_by_code(cleaned_code) is not None:
                raise ConflictError("A VAT rate with this code already exists.")

            rate = await repo.create(
                VatRate(
                    tenant_id=tenant_id,
                    code=cleaned_code,
                    name=name.strip(),
                    rate_percent=rate_percent,
                    is_vds_applicable=is_vds_applicable,
                    statutory_note=statutory_note.strip(),
                ),
                actor_id=actor_id,
            )
            await record_audit(
                session,
                tenant_id=tenant_id,
                actor_id=actor_id,
                action="vat.rate.created",
                resource_type="vat_rate",
                resource_id=rate.id,
                after_data={
                    "code": rate.code,
                    "rate_percent": rate_percent,
                    "is_vds_applicable": is_vds_applicable,
                },
            )
            return rate

    async def get_mushak_61(
        self,
        *,
        tenant_id: uuid.UUID,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[Mushak61Row]:
        async with self._database.transaction(tenant_id) as session:
            return await MushakReportRepository(session, tenant_id).purchase_register(
                date_from=date_from,
                date_to=date_to,
            )

    async def get_mushak_62(
        self,
        *,
        tenant_id: uuid.UUID,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[Mushak62Row]:
        async with self._database.transaction(tenant_id) as session:
            return await MushakReportRepository(session, tenant_id).sales_register(
                date_from=date_from,
                date_to=date_to,
            )

    async def get_mushak_63(
        self,
        *,
        tenant_id: uuid.UUID,
        invoice_id: uuid.UUID,
    ) -> Mushak63Data:
        async with self._database.transaction(tenant_id) as session:
            invoice = await SalesInvoiceRepository(session, tenant_id).get_with_lines(invoice_id)
            if invoice is None:
                raise NotFoundError("Sales invoice not found.")
            if invoice.status not in POSTED_STATUSES:
                raise BusinessRuleError(
                    "Mushak 6.3 Tax Invoice is only available for posted invoices."
                )

            customer = await CustomerRepository(session, tenant_id).get_by_id(invoice.customer_id)
            tenant = await TenantRepository(session, tenant_id).get_by_id(tenant_id)
            return Mushak63Data(
                invoice_id=invoice.id,
                invoice_no=invoice.invoice_no,
                invoice_date=invoice.invoice_date,
                seller_name=tenant.name if tenant is not None else "Nexzen ERP",
                customer_name=customer.name if customer is not None else "",
                customer_bin=customer.bin_no if customer is not None else "",
                customer_address=customer.address if customer is not None else "",
                lines=[
                    (
                        ln.line_no,
                        ln.description,
                        ln.quantity,
                        ln.unit_price,
                        ln.vat_rate_percent,
                        ln.line_subtotal,
                        ln.line_vat,
                        ln.line_total,
                    )
                    for ln in invoice.lines
                ],
                subtotal=invoice.subtotal,
                vat_total=invoice.vat_total,
                grand_total=invoice.grand_total,
            )
