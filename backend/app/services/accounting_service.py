"""Accounting & General Ledger business logic (double-entry enforcement, COA, Trial Balance)."""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from app.core.db import Database
from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.core.logging import get_logger
from app.core.query import (
    FilterRule,
    PaginationParams,
    SortParams,
    build_filters,
    build_order_by,
)
from app.models.accounting import Account, JournalEntry, JournalLine
from app.repositories.accounting import AccountRepository, JournalEntryRepository, TrialBalanceRow
from app.schemas.accounting import AccountType, JournalLineCreateRequest, NormalBalance
from app.services.audit_service import record_audit

logger = get_logger(__name__)

ZERO = Decimal("0.00")
MIN_JOURNAL_LINES = 2

NORMAL_BALANCE_BY_TYPE: dict[AccountType, NormalBalance] = {
    "asset": "debit",
    "expense": "debit",
    "liability": "credit",
    "equity": "credit",
    "revenue": "credit",
}


@dataclass(frozen=True, slots=True)
class DefaultAccountDef:
    code: str
    name: str
    account_type: AccountType
    is_group: bool = False
    description: str = ""


# Standard configurable baseline Chart of Accounts for Bangladeshi businesses.
# Tax/VAT ledgers are structural placeholders only; statutory rates are never hardcoded here.
DEFAULT_BD_COA: tuple[DefaultAccountDef, ...] = (
    DefaultAccountDef("1000", "Assets", "asset", is_group=True),
    DefaultAccountDef("1110", "Cash in Hand (BDT)", "asset"),
    DefaultAccountDef("1120", "Bank Account — Main (BDT)", "asset"),
    DefaultAccountDef("1200", "Accounts Receivable", "asset"),
    DefaultAccountDef("1300", "Inventory", "asset"),
    DefaultAccountDef("1400", "VAT Input Receivable (Configurable)", "asset"),
    DefaultAccountDef("2000", "Liabilities", "liability", is_group=True),
    DefaultAccountDef("2100", "Accounts Payable", "liability"),
    DefaultAccountDef("2200", "VAT Output Payable (Configurable)", "liability"),
    DefaultAccountDef("2210", "TDS / VDS Payable (Configurable)", "liability"),
    DefaultAccountDef("3000", "Equity", "equity", is_group=True),
    DefaultAccountDef("3100", "Owner's Capital / Share Capital", "equity"),
    DefaultAccountDef("3200", "Retained Earnings", "equity"),
    DefaultAccountDef("4000", "Revenue", "revenue", is_group=True),
    DefaultAccountDef("4100", "Sales Revenue", "revenue"),
    DefaultAccountDef("4200", "Service Revenue", "revenue"),
    DefaultAccountDef("5000", "Expenses", "expense", is_group=True),
    DefaultAccountDef("5100", "Cost of Goods Sold", "expense"),
    DefaultAccountDef("5200", "Salaries & Wages", "expense"),
    DefaultAccountDef("5300", "Office Rent & Utilities", "expense"),
)


def validate_double_entry_balance(
    lines: Sequence[JournalLineCreateRequest],
) -> tuple[Decimal, Decimal]:
    """Verify at least 2 lines and strict Decimal equality: total Debit == total Credit."""
    if len(lines) < MIN_JOURNAL_LINES:
        raise BusinessRuleError("A journal entry must contain at least 2 lines.")
    total_debit = sum((line.debit for line in lines), ZERO)
    total_credit = sum((line.credit for line in lines), ZERO)
    if total_debit <= ZERO:
        raise BusinessRuleError("Journal entry total must be greater than zero.")
    if total_debit != total_credit:
        raise BusinessRuleError(
            "Journal entry is not balanced: total debit must equal total credit.",
            details={
                "total_debit": str(total_debit),
                "total_credit": str(total_credit),
            },
        )
    return total_debit, total_credit


@dataclass(frozen=True, slots=True)
class TrialBalanceReport:
    as_of_date: date | None
    rows: list[TrialBalanceRow]
    grand_total_debit: Decimal
    grand_total_credit: Decimal

    @property
    def is_balanced(self) -> bool:
        return self.grand_total_debit == self.grand_total_credit


class AccountingService:
    """All Accounting & General Ledger business rules live here."""

    def __init__(self, database: Database) -> None:
        self._database = database

    async def seed_default_coa(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> tuple[int, int]:
        created = 0
        async with self._database.transaction(tenant_id) as session:
            repo = AccountRepository(session, tenant_id)
            for spec in DEFAULT_BD_COA:
                if await repo.get_by_code(spec.code) is None:
                    await repo.create(
                        Account(
                            tenant_id=tenant_id,
                            code=spec.code,
                            name=spec.name,
                            account_type=spec.account_type,
                            normal_balance=NORMAL_BALANCE_BY_TYPE[spec.account_type],
                            is_group=spec.is_group,
                            description=spec.description,
                        ),
                        actor_id=actor_id,
                    )
                    created += 1
            _, total = await repo.list_all(offset=0, limit=1)
            if created > 0:
                await record_audit(
                    session,
                    tenant_id=tenant_id,
                    actor_id=actor_id,
                    action="accounting.coa.seeded",
                    resource_type="account",
                    after_data={"created_count": created, "total_accounts": total},
                )
        return created, total

    async def list_accounts(
        self,
        *,
        tenant_id: uuid.UUID,
        pagination: PaginationParams,
        sort: SortParams,
        account_type: AccountType | None = None,
        search: str | None = None,
    ) -> tuple[list[Account], int]:
        order_by = build_order_by(
            sort,
            allowed={
                "code": Account.code,
                "name": Account.name,
                "account_type": Account.account_type,
                "created_at": Account.created_at,
            },
            default=[Account.code.asc()],
        )
        filters = build_filters(
            [
                FilterRule(column=Account.account_type, operator="eq", value=account_type),
                FilterRule(column=Account.name, operator="ilike", value=search),
            ]
        )
        async with self._database.transaction(tenant_id) as session:
            return await AccountRepository(session, tenant_id).list_all(
                offset=pagination.offset,
                limit=pagination.limit,
                filters=filters,
                order_by=order_by,
            )

    async def create_account(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        code: str,
        name: str,
        account_type: AccountType,
        parent_id: uuid.UUID | None = None,
        is_group: bool = False,
        description: str = "",
    ) -> Account:
        cleaned_code = code.strip()
        async with self._database.transaction(tenant_id) as session:
            repo = AccountRepository(session, tenant_id)
            if await repo.get_by_code(cleaned_code) is not None:
                raise ConflictError("An account with this code already exists.")

            if parent_id is not None:
                parent = await repo.get_by_id(parent_id)
                if parent is None:
                    raise NotFoundError("Parent account not found.")
                if not parent.is_group:
                    raise BusinessRuleError("Parent account must be a group account.")

            account = await repo.create(
                Account(
                    tenant_id=tenant_id,
                    code=cleaned_code,
                    name=name.strip(),
                    account_type=account_type,
                    normal_balance=NORMAL_BALANCE_BY_TYPE[account_type],
                    parent_id=parent_id,
                    is_group=is_group,
                    description=description.strip(),
                ),
                actor_id=actor_id,
            )
            await record_audit(
                session,
                tenant_id=tenant_id,
                actor_id=actor_id,
                action="accounting.account.created",
                resource_type="account",
                resource_id=account.id,
                after_data={
                    "code": account.code,
                    "name": account.name,
                    "account_type": account.account_type,
                    "is_group": account.is_group,
                },
            )
        return account

    async def list_journal_entries(
        self,
        *,
        tenant_id: uuid.UUID,
        pagination: PaginationParams,
        sort: SortParams,
        status_filter: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> tuple[list[JournalEntry], int]:
        order_by = build_order_by(
            sort,
            allowed={
                "entry_date": JournalEntry.entry_date,
                "voucher_no": JournalEntry.voucher_no,
                "created_at": JournalEntry.created_at,
            },
            default=[JournalEntry.entry_date.desc(), JournalEntry.created_at.desc()],
        )
        filters = build_filters(
            [
                FilterRule(column=JournalEntry.status, operator="eq", value=status_filter),
                FilterRule(column=JournalEntry.entry_date, operator="gte", value=date_from),
                FilterRule(column=JournalEntry.entry_date, operator="lte", value=date_to),
            ]
        )
        async with self._database.transaction(tenant_id) as session:
            return await JournalEntryRepository(session, tenant_id).list_all(
                offset=pagination.offset,
                limit=pagination.limit,
                filters=filters,
                order_by=order_by,
            )

    async def create_journal_entry(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        entry_date: date,
        reference: str,
        narration: str,
        lines: Sequence[JournalLineCreateRequest],
    ) -> JournalEntry:
        total_debit, _ = validate_double_entry_balance(lines)
        account_ids = list({line.account_id for line in lines})

        async with self._database.transaction(tenant_id) as session:
            acc_repo = AccountRepository(session, tenant_id)
            je_repo = JournalEntryRepository(session, tenant_id)

            accounts = await acc_repo.get_by_ids(account_ids)
            for acc_id in account_ids:
                acc = accounts.get(acc_id)
                if acc is None or not acc.is_active:
                    raise BusinessRuleError("One or more accounts do not exist or are inactive.")
                if acc.is_group:
                    raise BusinessRuleError(
                        f"Cannot post to group account '{acc.code} - {acc.name}'."
                    )

            seq = await je_repo.next_voucher_sequence(entry_date.year)
            voucher_no = f"JV-{entry_date.year}-{seq:06d}"

            entry = JournalEntry(
                tenant_id=tenant_id,
                voucher_no=voucher_no,
                entry_date=entry_date,
                reference=reference.strip(),
                narration=narration.strip(),
                status="draft",
            )
            entry = await je_repo.create(entry, actor_id=actor_id)

            for idx, line in enumerate(lines, start=1):
                session.add(
                    JournalLine(
                        tenant_id=tenant_id,
                        journal_entry_id=entry.id,
                        account_id=line.account_id,
                        line_no=idx,
                        description=line.description.strip(),
                        debit=line.debit,
                        credit=line.credit,
                        created_by=actor_id,
                        updated_by=actor_id,
                    )
                )
            await session.flush()
            loaded = await je_repo.get_with_lines(entry.id)
            if loaded is None:
                raise NotFoundError("Journal entry not found after creation.")

            await record_audit(
                session,
                tenant_id=tenant_id,
                actor_id=actor_id,
                action="accounting.journal.created",
                resource_type="journal_entry",
                resource_id=loaded.id,
                after_data={
                    "voucher_no": loaded.voucher_no,
                    "entry_date": loaded.entry_date,
                    "total_amount": total_debit,
                    "line_count": len(lines),
                    "status": loaded.status,
                },
            )
            return loaded

    async def post_journal_entry(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        entry_id: uuid.UUID,
    ) -> JournalEntry:
        async with self._database.transaction(tenant_id) as session:
            je_repo = JournalEntryRepository(session, tenant_id)
            entry = await je_repo.get_with_lines(entry_id)
            if entry is None:
                raise NotFoundError("Journal entry not found.")
            if entry.status != "draft":
                raise BusinessRuleError("Only draft journal entries can be posted.")

            total_debit = sum((line.debit for line in entry.lines), ZERO)
            total_credit = sum((line.credit for line in entry.lines), ZERO)
            if total_debit <= ZERO or total_debit != total_credit:
                raise BusinessRuleError("Cannot post an unbalanced journal entry.")

            entry.status = "posted"
            entry.posted_at = datetime.now(UTC)
            entry.posted_by = actor_id
            await je_repo.update(entry, actor_id=actor_id)

            await record_audit(
                session,
                tenant_id=tenant_id,
                actor_id=actor_id,
                action="accounting.journal.posted",
                resource_type="journal_entry",
                resource_id=entry.id,
                before_data={"status": "draft"},
                after_data={
                    "status": "posted",
                    "voucher_no": entry.voucher_no,
                    "total_amount": total_debit,
                },
            )
            loaded = await je_repo.get_with_lines(entry.id)
            if loaded is None:
                raise NotFoundError("Journal entry not found.")
            return loaded

    async def reverse_journal_entry(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        entry_id: uuid.UUID,
    ) -> JournalEntry:
        """Create a posted counter-entry swapping Debit/Credit and mark original reversed."""
        async with self._database.transaction(tenant_id) as session:
            je_repo = JournalEntryRepository(session, tenant_id)
            original = await je_repo.get_with_lines(entry_id)
            if original is None:
                raise NotFoundError("Journal entry not found.")
            if original.status != "posted":
                raise BusinessRuleError("Only posted journal entries can be reversed.")

            now = datetime.now(UTC)
            seq = await je_repo.next_voucher_sequence(now.year)
            rev_voucher_no = f"JV-{now.year}-{seq:06d}"

            reversal = await je_repo.create(
                JournalEntry(
                    tenant_id=tenant_id,
                    voucher_no=rev_voucher_no,
                    entry_date=now.date(),
                    reference=original.voucher_no,
                    narration=f"Reversal of {original.voucher_no}: {original.narration}",
                    status="posted",
                    posted_at=now,
                    posted_by=actor_id,
                    reversed_entry_id=original.id,
                ),
                actor_id=actor_id,
            )
            for idx, line in enumerate(original.lines, start=1):
                session.add(
                    JournalLine(
                        tenant_id=tenant_id,
                        journal_entry_id=reversal.id,
                        account_id=line.account_id,
                        line_no=idx,
                        description=f"Reversal: {line.description}".strip(),
                        debit=line.credit,
                        credit=line.debit,
                        created_by=actor_id,
                        updated_by=actor_id,
                    )
                )

            original.status = "reversed"
            await je_repo.update(original, actor_id=actor_id)
            await session.flush()

            await record_audit(
                session,
                tenant_id=tenant_id,
                actor_id=actor_id,
                action="accounting.journal.reversed",
                resource_type="journal_entry",
                resource_id=original.id,
                before_data={"status": "posted"},
                after_data={
                    "status": "reversed",
                    "reversal_entry_id": reversal.id,
                    "reversal_voucher_no": rev_voucher_no,
                },
            )
            loaded = await je_repo.get_with_lines(reversal.id)
            if loaded is None:
                raise NotFoundError("Reversal entry not found.")
            return loaded

    async def get_trial_balance(
        self,
        *,
        tenant_id: uuid.UUID,
        as_of_date: date | None = None,
    ) -> TrialBalanceReport:
        async with self._database.transaction(tenant_id) as session:
            rows = await JournalEntryRepository(session, tenant_id).trial_balance(
                as_of_date=as_of_date
            )
        grand_debit = sum((r.total_debit for r in rows), ZERO)
        grand_credit = sum((r.total_credit for r in rows), ZERO)
        return TrialBalanceReport(
            as_of_date=as_of_date,
            rows=rows,
            grand_total_debit=grand_debit,
            grand_total_credit=grand_credit,
        )
