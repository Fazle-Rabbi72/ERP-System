"""Financial Statements (P&L, Balance Sheet) & Executive Dashboard service."""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from app.core.db import Database
from app.repositories.reports import AccountBalanceRow, OperationalKpiSnapshot, ReportsRepository

ZERO = Decimal("0.00")
TWO_PLACES = Decimal("0.01")


def _q(value: Decimal) -> Decimal:
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


@dataclass(frozen=True, slots=True)
class StatementLine:
    account_id: uuid.UUID
    code: str
    name: str
    amount: Decimal


@dataclass(frozen=True, slots=True)
class ProfitAndLossReport:
    revenue_lines: list[StatementLine]
    expense_lines: list[StatementLine]
    total_revenue: Decimal
    total_expense: Decimal
    net_profit: Decimal


@dataclass(frozen=True, slots=True)
class BalanceSheetReport:
    asset_lines: list[StatementLine]
    liability_lines: list[StatementLine]
    equity_lines: list[StatementLine]
    current_earnings: Decimal
    total_assets: Decimal
    total_liabilities: Decimal
    total_equity: Decimal
    total_liabilities_and_equity: Decimal
    is_balanced: bool


def build_profit_and_loss(rows: Sequence[AccountBalanceRow]) -> ProfitAndLossReport:
    """Pure computation of Income Statement (P&L) from posted account balances."""
    revenue_lines: list[StatementLine] = []
    expense_lines: list[StatementLine] = []

    for row in rows:
        if row.account_type == "revenue":
            amt = _q(row.total_credit - row.total_debit)
            if amt != ZERO:
                revenue_lines.append(StatementLine(row.account_id, row.code, row.name, amt))
        elif row.account_type == "expense":
            amt = _q(row.total_debit - row.total_credit)
            if amt != ZERO:
                expense_lines.append(StatementLine(row.account_id, row.code, row.name, amt))

    total_revenue = _q(sum((line.amount for line in revenue_lines), ZERO))
    total_expense = _q(sum((line.amount for line in expense_lines), ZERO))
    net_profit = _q(total_revenue - total_expense)
    return ProfitAndLossReport(
        revenue_lines=revenue_lines,
        expense_lines=expense_lines,
        total_revenue=total_revenue,
        total_expense=total_expense,
        net_profit=net_profit,
    )


def build_balance_sheet(rows: Sequence[AccountBalanceRow]) -> BalanceSheetReport:
    """Pure computation of Balance Sheet verifying Assets = Liabilities + Equity."""
    asset_lines: list[StatementLine] = []
    liability_lines: list[StatementLine] = []
    equity_lines: list[StatementLine] = []

    for row in rows:
        if row.account_type == "asset":
            amt = _q(row.total_debit - row.total_credit)
            if amt != ZERO:
                asset_lines.append(StatementLine(row.account_id, row.code, row.name, amt))
        elif row.account_type == "liability":
            amt = _q(row.total_credit - row.total_debit)
            if amt != ZERO:
                liability_lines.append(StatementLine(row.account_id, row.code, row.name, amt))
        elif row.account_type == "equity":
            amt = _q(row.total_credit - row.total_debit)
            if amt != ZERO:
                equity_lines.append(StatementLine(row.account_id, row.code, row.name, amt))

    pnl = build_profit_and_loss(rows)
    current_earnings = pnl.net_profit
    total_assets = _q(sum((line.amount for line in asset_lines), ZERO))
    total_liabilities = _q(sum((line.amount for line in liability_lines), ZERO))
    total_equity = _q(sum((line.amount for line in equity_lines), ZERO) + current_earnings)
    total_l_and_e = _q(total_liabilities + total_equity)

    return BalanceSheetReport(
        asset_lines=asset_lines,
        liability_lines=liability_lines,
        equity_lines=equity_lines,
        current_earnings=current_earnings,
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        total_equity=total_equity,
        total_liabilities_and_equity=total_l_and_e,
        is_balanced=total_assets == total_l_and_e,
    )


class ReportsService:
    """Executive financial statements and cross-module KPI aggregation."""

    def __init__(self, database: Database) -> None:
        self._database = database

    async def profit_and_loss(
        self,
        *,
        tenant_id: uuid.UUID,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> ProfitAndLossReport:
        async with self._database.transaction(tenant_id) as session:
            rows = await ReportsRepository(session, tenant_id).ledger_balances(
                date_from=date_from, date_to=date_to
            )
            return build_profit_and_loss(rows)

    async def balance_sheet(
        self,
        *,
        tenant_id: uuid.UUID,
        as_of_date: date | None = None,
    ) -> BalanceSheetReport:
        async with self._database.transaction(tenant_id) as session:
            rows = await ReportsRepository(session, tenant_id).ledger_balances(date_to=as_of_date)
            return build_balance_sheet(rows)

    async def dashboard_summary(
        self,
        *,
        tenant_id: uuid.UUID,
    ) -> tuple[ProfitAndLossReport, BalanceSheetReport, OperationalKpiSnapshot]:
        async with self._database.transaction(tenant_id) as session:
            repo = ReportsRepository(session, tenant_id)
            rows = await repo.ledger_balances()
            kpis = await repo.operational_kpis()
            return build_profit_and_loss(rows), build_balance_sheet(rows), kpis
