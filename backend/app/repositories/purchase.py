"""Repositories for Purchase & Supplier (suppliers, bills, supplier payments)."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.purchase import PurchaseBill, Supplier, SupplierPayment
from app.repositories.base import BaseRepository


class SupplierRepository(BaseRepository[Supplier]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(session, tenant_id, Supplier)

    async def get_by_code(self, code: str) -> Supplier | None:
        stmt = self._base_query().where(Supplier.code == code)
        return (await self._session.execute(stmt)).scalar_one_or_none()


class PurchaseBillRepository(BaseRepository[PurchaseBill]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(session, tenant_id, PurchaseBill)

    async def get_with_lines(self, bill_id: uuid.UUID) -> PurchaseBill | None:
        stmt = (
            self._base_query()
            .options(selectinload(PurchaseBill.lines))
            .where(PurchaseBill.id == bill_id)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def next_bill_sequence(self, year: int) -> int:
        prefix = f"BILL-{year}-"
        stmt = select(func.count(PurchaseBill.id)).where(
            PurchaseBill.tenant_id == self._tenant_id,
            PurchaseBill.bill_no.like(f"{prefix}%"),
        )
        return int((await self._session.execute(stmt)).scalar_one()) + 1


class SupplierPaymentRepository(BaseRepository[SupplierPayment]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(session, tenant_id, SupplierPayment)

    async def next_payment_sequence(self, year: int) -> int:
        prefix = f"PAY-{year}-"
        stmt = select(func.count(SupplierPayment.id)).where(
            SupplierPayment.tenant_id == self._tenant_id,
            SupplierPayment.payment_no.like(f"{prefix}%"),
        )
        return int((await self._session.execute(stmt)).scalar_one()) + 1
