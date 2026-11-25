"""Pydantic schemas for Financial Statements (P&L, Balance Sheet) & Executive Dashboard."""

import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, field_serializer

_TWO_PLACES = Decimal("0.01")


def _fmt_money(value: Decimal) -> str:
    return str(value.quantize(_TWO_PLACES))


class StatementLineResponse(BaseModel):
    account_id: uuid.UUID
    code: str
    name: str
    amount: Decimal

    @field_serializer("amount")
    def _serialize_money(self, value: Decimal) -> str:
        return _fmt_money(value)


class ProfitAndLossResponse(BaseModel):
    date_from: date | None
    date_to: date | None
    revenue_lines: list[StatementLineResponse]
    expense_lines: list[StatementLineResponse]
    total_revenue: Decimal
    total_expense: Decimal
    net_profit: Decimal

    @field_serializer("total_revenue", "total_expense", "net_profit")
    def _serialize_money(self, value: Decimal) -> str:
        return _fmt_money(value)


class BalanceSheetResponse(BaseModel):
    as_of_date: date | None
    asset_lines: list[StatementLineResponse]
    liability_lines: list[StatementLineResponse]
    equity_lines: list[StatementLineResponse]
    current_earnings: Decimal
    total_assets: Decimal
    total_liabilities: Decimal
    total_equity: Decimal
    total_liabilities_and_equity: Decimal
    is_balanced: bool

    @field_serializer(
        "current_earnings",
        "total_assets",
        "total_liabilities",
        "total_equity",
        "total_liabilities_and_equity",
    )
    def _serialize_money(self, value: Decimal) -> str:
        return _fmt_money(value)


class MonthlyTrendPointResponse(BaseModel):
    month: str
    revenue: Decimal
    expense: Decimal
    net_profit: Decimal

    @field_serializer("revenue", "expense", "net_profit")
    def _serialize_money(self, value: Decimal) -> str:
        return _fmt_money(value)


class DashboardSummaryResponse(BaseModel):
    total_revenue: Decimal
    total_expense: Decimal
    net_profit: Decimal
    total_assets: Decimal
    total_liabilities: Decimal
    accounts_receivable_due: Decimal
    accounts_payable_due: Decimal
    total_accounts_count: int
    active_employees_count: int
    low_stock_products_count: int
    monthly_trend: list[MonthlyTrendPointResponse]
    expense_breakdown: list[StatementLineResponse]

    @field_serializer(
        "total_revenue",
        "total_expense",
        "net_profit",
        "total_assets",
        "total_liabilities",
        "accounts_receivable_due",
        "accounts_payable_due",
    )
    def _serialize_money(self, value: Decimal) -> str:
        return _fmt_money(value)
