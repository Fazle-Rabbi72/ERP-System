"""Financial Statements & Executive Dashboard HTTP router."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_reports_service, require_permission
from app.core.permissions import PERM_ACCOUNTING_REPORTS_READ
from app.core.security import TokenPayload
from app.schemas.reports import (
    BalanceSheetResponse,
    DashboardSummaryResponse,
    ProfitAndLossResponse,
    StatementLineResponse,
)
from app.services.reports_service import ReportsService, StatementLine

router = APIRouter(prefix="/reports", tags=["reports"])


def _map_lines(lines: list[StatementLine]) -> list[StatementLineResponse]:
    return [
        StatementLineResponse(
            account_id=item.account_id,
            code=item.code,
            name=item.name,
            amount=item.amount,
        )
        for item in lines
    ]


@router.get("/profit-and-loss", response_model=ProfitAndLossResponse)
async def get_profit_and_loss(
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_ACCOUNTING_REPORTS_READ))],
    service: Annotated[ReportsService, Depends(get_reports_service)],
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> ProfitAndLossResponse:
    report = await service.profit_and_loss(
        tenant_id=auth.tenant_id, date_from=date_from, date_to=date_to
    )
    return ProfitAndLossResponse(
        date_from=date_from,
        date_to=date_to,
        revenue_lines=_map_lines(report.revenue_lines),
        expense_lines=_map_lines(report.expense_lines),
        total_revenue=report.total_revenue,
        total_expense=report.total_expense,
        net_profit=report.net_profit,
    )


@router.get("/balance-sheet", response_model=BalanceSheetResponse)
async def get_balance_sheet(
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_ACCOUNTING_REPORTS_READ))],
    service: Annotated[ReportsService, Depends(get_reports_service)],
    as_of_date: Annotated[date | None, Query()] = None,
) -> BalanceSheetResponse:
    report = await service.balance_sheet(tenant_id=auth.tenant_id, as_of_date=as_of_date)
    return BalanceSheetResponse(
        as_of_date=as_of_date,
        asset_lines=_map_lines(report.asset_lines),
        liability_lines=_map_lines(report.liability_lines),
        equity_lines=_map_lines(report.equity_lines),
        current_earnings=report.current_earnings,
        total_assets=report.total_assets,
        total_liabilities=report.total_liabilities,
        total_equity=report.total_equity,
        total_liabilities_and_equity=report.total_liabilities_and_equity,
        is_balanced=report.is_balanced,
    )


@router.get("/dashboard-summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    auth: Annotated[TokenPayload, Depends(require_permission(PERM_ACCOUNTING_REPORTS_READ))],
    service: Annotated[ReportsService, Depends(get_reports_service)],
) -> DashboardSummaryResponse:
    pnl, bs, kpis = await service.dashboard_summary(tenant_id=auth.tenant_id)
    return DashboardSummaryResponse(
        total_revenue=pnl.total_revenue,
        total_expense=pnl.total_expense,
        net_profit=pnl.net_profit,
        total_assets=bs.total_assets,
        total_liabilities=bs.total_liabilities,
        accounts_receivable_due=kpis.accounts_receivable_due,
        accounts_payable_due=kpis.accounts_payable_due,
        total_accounts_count=kpis.total_accounts_count,
        active_employees_count=kpis.active_employees_count,
        low_stock_products_count=kpis.low_stock_products_count,
    )
