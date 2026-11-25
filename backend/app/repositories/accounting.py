"""Repositories for Accounting & General Ledger (Chart of Accounts, Journals, Trial Balance)."""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.accounting import Account, JournalEntry, JournalLine
from app.repositories.base import BaseRepository


@dataclass(frozen=True, slots=True)
class TrialBalanceRow:
    account_id: uuid.UUID
    code: str
    name: str
    account_type: str
    normal_balance: str
    total_debit: Decimal
    total_credit: Decimal


class AccountRepository(BaseRepository[Account]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(session, tenant_id, Account)

    async def get_by_code(self, code: str) -> Account | None:
        stmt = self._base_query().where(Account.code == code)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_by_ids(self, ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, Account]:
        if not ids:
            return {}
        stmt = self._base_query().where(Account.id.in_(ids))
        rows = (await self._session.execute(stmt)).scalars().all()
        return {acc.id: acc for acc in rows}


class JournalEntryRepository(BaseRepository[JournalEntry]):
    def __init__(self, session: AsyncSession, tenant_id: uuid.UUID) -> None:
        super().__init__(session, tenant_id, JournalEntry)

    async def get_with_lines(self, entry_id: uuid.UUID) -> JournalEntry | None:
        stmt = (
            self._base_query()
            .options(selectinload(JournalEntry.lines))
            .where(JournalEntry.id == entry_id)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def next_voucher_sequence(self, year: int) -> int:
        prefix = f"JV-{year}-"
        stmt = select(func.count(JournalEntry.id)).where(
            JournalEntry.tenant_id == self._tenant_id,
            JournalEntry.voucher_no.like(f"{prefix}%"),
        )
        count = int((await self._session.execute(stmt)).scalar_one())
        return count + 1

    async def trial_balance(self, *, as_of_date: date | None = None) -> list[TrialBalanceRow]:
        """Aggregate posted journal lines by account using exact SQL NUMERIC(18,2)."""
        stmt = (
            select(
                Account.id,
                Account.code,
                Account.name,
                Account.account_type,
                Account.normal_balance,
                func.coalesce(func.sum(JournalLine.debit), Decimal("0.00")).label("total_debit"),
                func.coalesce(func.sum(JournalLine.credit), Decimal("0.00")).label("total_credit"),
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
                JournalEntry.status.in_(("posted", "reversed")),
            )
            .group_by(
                Account.id,
                Account.code,
                Account.name,
                Account.account_type,
                Account.normal_balance,
            )
            .order_by(Account.code.asc())
        )
        if as_of_date is not None:
            stmt = stmt.where(JournalEntry.entry_date <= as_of_date)

        rows = (await self._session.execute(stmt)).all()
        return [
            TrialBalanceRow(
                account_id=row.id,
                code=row.code,
                name=row.name,
                account_type=row.account_type,
                normal_balance=row.normal_balance,
                total_debit=Decimal(row.total_debit),
                total_credit=Decimal(row.total_credit),
            )
            for row in rows
        ]
