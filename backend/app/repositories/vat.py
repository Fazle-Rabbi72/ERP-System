"""Repositories for configurable VAT rates and Mushak 6.1 / 6.2 / 9.1 queries."""

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.purchase import PurchaseBill, Supplier
from app.models.sales import Customer, SalesInvoice
from app.models.vat import VatRate
from app.repositories.base import BaseRepository

POSTED_STATUSES = ("posted", "partially_paid", "paid")


@dataclass(frozen=True, slots=True)
class Mushak61Row:
    bill_id: uuid.UUID
    bill_no: str
    bill_date: date
    supplier_bill_ref: str
    supplier_name: str
    supplier_bin: str
    taxable_value: Decimal
    input_vat: Decimal
    vds_amount: Decimal
    tds_amount: Decimal
    gross_total: Decimal


@dataclass(frozen=True, slots=True)
class Mushak62Row:
    invoice_id: uuid.UUID
    invoice_no: str
    invoice_date: date
    customer_name: str
    customer_bin: str
    taxable_value: Decimal
    output_vat: Decimal
    grand_total: Decimal


class VatRateRepository(BaseRepository[VatRate]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(session, tenant_id, VatRate)

    async def get_by_code(self, code: str) -> VatRate | None:
        stmt = self._base_query().where(VatRate.code == code)
        return (await self._session.execute(stmt)).scalar_one_or_none()


class MushakReportRepository:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._session = session
        self._tenant_id = tenant_id

    async def purchase_register(
        self,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[Mushak61Row]:
        stmt = (
            select(
                PurchaseBill.id,
                PurchaseBill.bill_no,
                PurchaseBill.bill_date,
                PurchaseBill.supplier_bill_ref,
                Supplier.name.label("supplier_name"),
                Supplier.bin_no.label("supplier_bin"),
                PurchaseBill.subtotal,
                PurchaseBill.vat_total,
                PurchaseBill.vds_amount,
                PurchaseBill.tds_amount,
                PurchaseBill.gross_total,
            )
            .join(Supplier, Supplier.id == PurchaseBill.supplier_id)
            .where(
                PurchaseBill.tenant_id == self._tenant_id,
                PurchaseBill.is_deleted.is_(False),
                PurchaseBill.status.in_(POSTED_STATUSES),
            )
            .order_by(PurchaseBill.bill_date.asc(), PurchaseBill.bill_no.asc())
        )
        if date_from is not None:
            stmt = stmt.where(PurchaseBill.bill_date >= date_from)
        if date_to is not None:
            stmt = stmt.where(PurchaseBill.bill_date <= date_to)

        rows = (await self._session.execute(stmt)).all()
        return [
            Mushak61Row(
                bill_id=r.id,
                bill_no=r.bill_no,
                bill_date=r.bill_date,
                supplier_bill_ref=r.supplier_bill_ref,
                supplier_name=r.supplier_name,
                supplier_bin=r.supplier_bin,
                taxable_value=Decimal(r.subtotal),
                input_vat=Decimal(r.vat_total),
                vds_amount=Decimal(r.vds_amount),
                tds_amount=Decimal(r.tds_amount),
                gross_total=Decimal(r.gross_total),
            )
            for r in rows
        ]

    async def sales_register(
        self,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[Mushak62Row]:
        stmt = (
            select(
                SalesInvoice.id,
                SalesInvoice.invoice_no,
                SalesInvoice.invoice_date,
                Customer.name.label("customer_name"),
                Customer.bin_no.label("customer_bin"),
                SalesInvoice.subtotal,
                SalesInvoice.vat_total,
                SalesInvoice.grand_total,
            )
            .join(Customer, Customer.id == SalesInvoice.customer_id)
            .where(
                SalesInvoice.tenant_id == self._tenant_id,
                SalesInvoice.is_deleted.is_(False),
                SalesInvoice.status.in_(POSTED_STATUSES),
            )
            .order_by(SalesInvoice.invoice_date.asc(), SalesInvoice.invoice_no.asc())
        )
        if date_from is not None:
            stmt = stmt.where(SalesInvoice.invoice_date >= date_from)
        if date_to is not None:
            stmt = stmt.where(SalesInvoice.invoice_date <= date_to)

        rows = (await self._session.execute(stmt)).all()
        return [
            Mushak62Row(
                invoice_id=r.id,
                invoice_no=r.invoice_no,
                invoice_date=r.invoice_date,
                customer_name=r.customer_name,
                customer_bin=r.customer_bin,
                taxable_value=Decimal(r.subtotal),
                output_vat=Decimal(r.vat_total),
                grand_total=Decimal(r.grand_total),
            )
            for r in rows
        ]
