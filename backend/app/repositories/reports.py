"""Repository queries for Financial Statements (P&L, Balance Sheet) & Executive Dashboard."""

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accounting import Account, JournalEntry, JournalLine
from app.models.hr import Employee
from app.models.inventory import Product, StockMovement
from app.models.purchase import PurchaseBill
from app.models.sales import SalesInvoice

ZERO = Decimal("0.00")
POSTED_JOURNAL_STATUSES = ("posted", "reversed")
OPEN_DOC_STATUSES = ("posted", "partially_paid")


@dataclass(frozen=True, slots=True)
class AccountBalanceRow:
    account_id: uuid.UUID
    code: str
    name: str
    account_type: str
    total_debit: Decimal
    total_credit: Decimal


@dataclass(frozen=True, slots=True)
class OperationalKpiSnapshot:
    total_accounts_count: int
    accounts_receivable_due: Decimal
    accounts_payable_due: Decimal
    active_employees_count: int
    low_stock_products_count: int


class ReportsRepository:
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        self._session = session
        self._tenant_id = tenant_id

    async def ledger_balances(
        self,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[AccountBalanceRow]:
        stmt = (
            select(
                Account.id,
                Account.code,
                Account.name,
                Account.account_type,
                func.coalesce(func.sum(JournalLine.debit), ZERO).label("total_debit"),
                func.coalesce(func.sum(JournalLine.credit), ZERO).label("total_credit"),
            )
            .join(JournalLine, JournalLine.account_id == Account.id)
            .join(JournalEntry, JournalEntry.id == JournalLine.journal_entry_id)
            .where(
                Account.tenant_id == self._tenant_id,
                Account.is_deleted.is_(False),
                JournalLine.tenant_id == self._tenant_id,
                JournalLine.is_deleted.is_(False),
                JournalEntry.tenant_id == self._tenant_id,
                JournalEntry.is_deleted.is_(False),
                JournalEntry.status.in_(POSTED_JOURNAL_STATUSES),
            )
            .group_by(Account.id, Account.code, Account.name, Account.account_type)
            .order_by(Account.code.asc())
        )
        if date_from is not None:
            stmt = stmt.where(JournalEntry.entry_date >= date_from)
        if date_to is not None:
            stmt = stmt.where(JournalEntry.entry_date <= date_to)

        rows = (await self._session.execute(stmt)).all()
        return [
            AccountBalanceRow(
                account_id=r.id,
                code=r.code,
                name=r.name,
                account_type=r.account_type,
                total_debit=Decimal(r.total_debit),
                total_credit=Decimal(r.total_credit),
            )
            for r in rows
        ]

    async def operational_kpis(self) -> OperationalKpiSnapshot:
        acc_count = int(
            (
                await self._session.execute(
                    select(func.count(Account.id)).where(
                        Account.tenant_id == self._tenant_id,
                        Account.is_deleted.is_(False),
                        Account.is_active.is_(True),
                    )
                )
            ).scalar_one()
        )

        ar_due = Decimal(
            (
                await self._session.execute(
                    select(
                        func.coalesce(
                            func.sum(SalesInvoice.grand_total - SalesInvoice.paid_amount), ZERO
                        )
                    ).where(
                        SalesInvoice.tenant_id == self._tenant_id,
                        SalesInvoice.is_deleted.is_(False),
                        SalesInvoice.status.in_(OPEN_DOC_STATUSES),
                    )
                )
            ).scalar_one()
        )

        ap_due = Decimal(
            (
                await self._session.execute(
                    select(
                        func.coalesce(
                            func.sum(PurchaseBill.net_payable - PurchaseBill.paid_amount), ZERO
                        )
                    ).where(
                        PurchaseBill.tenant_id == self._tenant_id,
                        PurchaseBill.is_deleted.is_(False),
                        PurchaseBill.status.in_(OPEN_DOC_STATUSES),
                    )
                )
            ).scalar_one()
        )

        emp_count = int(
            (
                await self._session.execute(
                    select(func.count(Employee.id)).where(
                        Employee.tenant_id == self._tenant_id,
                        Employee.is_deleted.is_(False),
                        Employee.is_active.is_(True),
                    )
                )
            ).scalar_one()
        )

        # Low-stock active products: on_hand <= reorder_level (when reorder_level > 0)
        stock_subq = (
            select(
                StockMovement.product_id.label("product_id"),
                func.coalesce(func.sum(StockMovement.quantity), ZERO).label("on_hand"),
            )
            .where(
                StockMovement.tenant_id == self._tenant_id,
                StockMovement.is_deleted.is_(False),
            )
            .group_by(StockMovement.product_id)
            .subquery()
        )
        low_stock_rows = (
            await self._session.execute(
                select(
                    Product.reorder_level,
                    func.coalesce(stock_subq.c.on_hand, ZERO).label("on_hand"),
                )
                .outerjoin(stock_subq, stock_subq.c.product_id == Product.id)
                .where(
                    Product.tenant_id == self._tenant_id,
                    Product.is_deleted.is_(False),
                    Product.is_active.is_(True),
                    Product.reorder_level > ZERO,
                )
            )
        ).all()
        low_stock_count = sum(
            1 for r in low_stock_rows if Decimal(r.on_hand) <= Decimal(r.reorder_level)
        )

        return OperationalKpiSnapshot(
            total_accounts_count=acc_count,
            accounts_receivable_due=ar_due,
            accounts_payable_due=ap_due,
            active_employees_count=emp_count,
            low_stock_products_count=low_stock_count,
        )
