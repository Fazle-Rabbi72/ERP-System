"""Repositories for Sales & Invoicing (customers, invoices, payments)."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.sales import Customer, CustomerPayment, SalesInvoice
from app.repositories.base import BaseRepository


class CustomerRepository(BaseRepository[Customer]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(session, tenant_id, Customer)

    async def get_by_code(self, code: str) -> Customer | None:
        stmt = self._base_query().where(Customer.code == code)
        return (await self._session.execute(stmt)).scalar_one_or_none()


class SalesInvoiceRepository(BaseRepository[SalesInvoice]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(session, tenant_id, SalesInvoice)

    async def get_with_lines(self, invoice_id: uuid.UUID) -> SalesInvoice | None:
        stmt = (
            self._base_query()
            .options(selectinload(SalesInvoice.lines))
            .where(SalesInvoice.id == invoice_id)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def next_invoice_sequence(self, year: int) -> int:
        prefix = f"INV-{year}-"
        stmt = select(func.count(SalesInvoice.id)).where(
            SalesInvoice.tenant_id == self._tenant_id,
            SalesInvoice.invoice_no.like(f"{prefix}%"),
        )
        return int((await self._session.execute(stmt)).scalar_one()) + 1


class CustomerPaymentRepository(BaseRepository[CustomerPayment]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(session, tenant_id, CustomerPayment)

    async def next_payment_sequence(self, year: int) -> int:
        prefix = f"RCPT-{year}-"
        stmt = select(func.count(CustomerPayment.id)).where(
            CustomerPayment.tenant_id == self._tenant_id,
            CustomerPayment.payment_no.like(f"{prefix}%"),
        )
        return int((await self._session.execute(stmt)).scalar_one()) + 1
