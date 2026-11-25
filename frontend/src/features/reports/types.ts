export interface StatementLine {
  account_id: string;
  code: string;
  name: string;
  amount: string;
}

export interface ProfitAndLossReport {
  date_from: string | null;
  date_to: string | null;
  revenue_lines: StatementLine[];
  expense_lines: StatementLine[];
  total_revenue: string;
  total_expense: string;
  net_profit: string;
}

export interface BalanceSheetReport {
  as_of_date: string | null;
  asset_lines: StatementLine[];
  liability_lines: StatementLine[];
  equity_lines: StatementLine[];
  current_earnings: string;
  total_assets: string;
  total_liabilities: string;
  total_equity: string;
  total_liabilities_and_equity: string;
  is_balanced: boolean;
}

export interface MonthlyTrendPoint {
  month: string;
  revenue: string;
  expense: string;
  net_profit: string;
}

export interface DashboardSummary {
  total_revenue: string;
  total_expense: string;
  net_profit: string;
  total_assets: string;
  total_liabilities: string;
  accounts_receivable_due: string;
  accounts_payable_due: string;
  total_accounts_count: number;
  active_employees_count: number;
  low_stock_products_count: number;
  monthly_trend: MonthlyTrendPoint[];
  expense_breakdown: StatementLine[];
}
