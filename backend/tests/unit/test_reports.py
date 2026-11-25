"""Unit tests for Financial Statements (P&L and Balance Sheet) pure math."""

import uuid
from decimal import Decimal

from app.repositories.reports import AccountBalanceRow
from app.services.reports_service import build_balance_sheet, build_profit_and_loss


def test_profit_and_loss_and_balance_sheet_equation() -> None:
    rows = [
        AccountBalanceRow(
            uuid.uuid4(),
            "1110",
            "Cash in Hand",
            "asset",
            Decimal("200000.00"),
            Decimal("80000.00"),
        ),
        AccountBalanceRow(
            uuid.uuid4(),
            "2100",
            "Accounts Payable",
            "liability",
            Decimal("0.00"),
            Decimal("20000.00"),
        ),
        AccountBalanceRow(
            uuid.uuid4(),
            "3100",
            "Owner Capital",
            "equity",
            Decimal("0.00"),
            Decimal("50000.00"),
        ),
        AccountBalanceRow(
            uuid.uuid4(),
            "4100",
            "Sales Revenue",
            "revenue",
            Decimal("0.00"),
            Decimal("150000.00"),
        ),
        AccountBalanceRow(
            uuid.uuid4(),
            "5200",
            "Salaries & Wages",
            "expense",
            Decimal("100000.00"),
            Decimal("0.00"),
        ),
    ]

    pnl = build_profit_and_loss(rows)
    assert pnl.total_revenue == Decimal("150000.00")
    assert pnl.total_expense == Decimal("100000.00")
    assert pnl.net_profit == Decimal("50000.00")

    bs = build_balance_sheet(rows)
    assert bs.total_assets == Decimal("120000.00")
    assert bs.total_liabilities == Decimal("20000.00")
    assert bs.current_earnings == Decimal("50000.00")
    assert bs.total_equity == Decimal("100000.00")
    assert bs.total_liabilities_and_equity == Decimal("120000.00")
    assert bs.is_balanced is True
