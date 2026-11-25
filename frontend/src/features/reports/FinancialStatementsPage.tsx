import { useQuery } from "@tanstack/react-query";
import { Printer } from "lucide-react";
import * as React from "react";
import { useTranslation } from "react-i18next";

import { EmptyState } from "@/components/states/EmptyState";
import { ErrorState } from "@/components/states/ErrorState";
import { TableSkeleton } from "@/components/states/TableSkeleton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuthStore } from "@/features/auth/store";
import type { BalanceSheetReport, ProfitAndLossReport } from "@/features/reports/types";
import { apiRequest } from "@/lib/api";
import { formatBDT } from "@/lib/format";

type StatementTab = "pnl" | "bs";

export function FinancialStatementsPage(): React.JSX.Element {
  const { t } = useTranslation();
  const accessToken = useAuthStore((s) => s.accessToken);
  const banglaDigits = useAuthStore((s) => s.banglaDigits);

  const [tab, setTab] = React.useState<StatementTab>("pnl");
  const [dateFrom, setDateFrom] = React.useState("");
  const [dateTo, setDateTo] = React.useState("");
  const [asOfDate, setAsOfDate] = React.useState("");

  const pnlParams = new URLSearchParams();
  if (dateFrom) pnlParams.set("date_from", dateFrom);
  if (dateTo) pnlParams.set("date_to", dateTo);
  const pnlQs = pnlParams.toString() ? `?${pnlParams.toString()}` : "";

  const bsQs = asOfDate ? `?as_of_date=${encodeURIComponent(asOfDate)}` : "";

  const pnlQuery = useQuery({
    queryKey: ["reports", "profit-and-loss", dateFrom, dateTo],
    queryFn: ({ signal }) =>
      apiRequest<ProfitAndLossReport>(`/reports/profit-and-loss${pnlQs}`, {
        accessToken,
        signal,
      }),
    enabled: Boolean(accessToken) && tab === "pnl",
  });

  const bsQuery = useQuery({
    queryKey: ["reports", "balance-sheet", asOfDate],
    queryFn: ({ signal }) =>
      apiRequest<BalanceSheetReport>(`/reports/balance-sheet${bsQs}`, {
        accessToken,
        signal,
      }),
    enabled: Boolean(accessToken) && tab === "bs",
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4 print:hidden">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{t("reports.title")}</h1>
          <p className="text-sm text-muted-foreground">{t("reports.subtitle")}</p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            window.print();
          }}
        >
          <Printer className="h-4 w-4" aria-hidden="true" />
          {t("reports.print")}
        </Button>
      </div>

      <div className="flex flex-wrap items-end justify-between gap-4 border-b border-border pb-3 print:hidden">
        <div className="flex gap-2" role="tablist">
          <Button
            role="tab"
            aria-selected={tab === "pnl"}
            variant={tab === "pnl" ? "default" : "outline"}
            size="sm"
            onClick={() => {
              setTab("pnl");
            }}
          >
            {t("reports.tabPnl")}
          </Button>
          <Button
            role="tab"
            aria-selected={tab === "bs"}
            variant={tab === "bs" ? "default" : "outline"}
            size="sm"
            onClick={() => {
              setTab("bs");
            }}
          >
            {t("reports.tabBalanceSheet")}
          </Button>
        </div>

        {tab === "pnl" ? (
          <div className="flex flex-wrap items-end gap-3">
            <div className="space-y-1">
              <Label htmlFor="pnl-from">{t("vat.dateFrom")}</Label>
              <Input
                id="pnl-from"
                type="date"
                value={dateFrom}
                onChange={(e) => {
                  setDateFrom(e.target.value);
                }}
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="pnl-to">{t("vat.dateTo")}</Label>
              <Input
                id="pnl-to"
                type="date"
                value={dateTo}
                onChange={(e) => {
                  setDateTo(e.target.value);
                }}
              />
            </div>
          </div>
        ) : (
          <div className="space-y-1">
            <Label htmlFor="bs-as-of">{t("accounting.asOfDate")}</Label>
            <Input
              id="bs-as-of"
              type="date"
              value={asOfDate}
              onChange={(e) => {
                setAsOfDate(e.target.value);
              }}
            />
          </div>
        )}
      </div>

      {/* PROFIT & LOSS */}
      {tab === "pnl" ? (
        <Card>
          <CardHeader>
            <CardTitle>{t("reports.pnlTitle")}</CardTitle>
          </CardHeader>
          <CardContent>
            {pnlQuery.isLoading ? (
              <TableSkeleton rows={5} columns={3} />
            ) : pnlQuery.isError ? (
              <ErrorState
                title={t("reports.loadError")}
                message={pnlQuery.error.message}
                retryLabel={t("dashboard.retry")}
                onRetry={() => void pnlQuery.refetch()}
              />
            ) : !pnlQuery.data ||
              (pnlQuery.data.revenue_lines.length === 0 &&
                pnlQuery.data.expense_lines.length === 0) ? (
              <EmptyState
                title={t("reports.emptyTitle")}
                description={t("reports.emptyDesc")}
              />
            ) : (
              <div className="space-y-6">
                <div>
                  <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                    {t("reports.revenueSection")}
                  </h2>
                  <table className="w-full text-left text-sm">
                    <tbody className="divide-y divide-border">
                      {pnlQuery.data.revenue_lines.map((line) => (
                        <tr key={line.account_id}>
                          <td className="w-28 py-2 font-mono text-xs">{line.code}</td>
                          <td className="py-2 font-medium">{line.name}</td>
                          <td className="py-2 text-right tabular-nums">
                            {formatBDT(line.amount, { banglaDigits })}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot className="border-t border-border font-semibold">
                      <tr>
                        <td colSpan={2} className="pt-2">
                          {t("reports.totalRevenue")}
                        </td>
                        <td className="pt-2 text-right tabular-nums">
                          {formatBDT(pnlQuery.data.total_revenue, { banglaDigits })}
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                </div>

                <div>
                  <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                    {t("reports.expenseSection")}
                  </h2>
                  <table className="w-full text-left text-sm">
                    <tbody className="divide-y divide-border">
                      {pnlQuery.data.expense_lines.map((line) => (
                        <tr key={line.account_id}>
                          <td className="w-28 py-2 font-mono text-xs">{line.code}</td>
                          <td className="py-2 font-medium">{line.name}</td>
                          <td className="py-2 text-right tabular-nums">
                            {formatBDT(line.amount, { banglaDigits })}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot className="border-t border-border font-semibold">
                      <tr>
                        <td colSpan={2} className="pt-2">
                          {t("reports.totalExpense")}
                        </td>
                        <td className="pt-2 text-right tabular-nums">
                          {formatBDT(pnlQuery.data.total_expense, { banglaDigits })}
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                </div>

                <div className="flex items-center justify-between rounded-lg bg-secondary/50 p-4 text-base font-bold">
                  <span>{t("reports.netProfit")}</span>
                  <span className="tabular-nums text-primary">
                    {formatBDT(pnlQuery.data.net_profit, { banglaDigits })}
                  </span>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      ) : null}

      {/* BALANCE SHEET */}
      {tab === "bs" ? (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>{t("reports.bsTitle")}</CardTitle>
            {bsQuery.data ? (
              <Badge variant={bsQuery.data.is_balanced ? "default" : "secondary"}>
                {bsQuery.data.is_balanced
                  ? t("accounting.balanced")
                  : t("accounting.outOfBalance")}
              </Badge>
            ) : null}
          </CardHeader>
          <CardContent>
            {bsQuery.isLoading ? (
              <TableSkeleton rows={5} columns={3} />
            ) : bsQuery.isError ? (
              <ErrorState
                title={t("reports.loadError")}
                message={bsQuery.error.message}
                retryLabel={t("dashboard.retry")}
                onRetry={() => void bsQuery.refetch()}
              />
            ) : !bsQuery.data ||
              (bsQuery.data.asset_lines.length === 0 &&
                bsQuery.data.liability_lines.length === 0 &&
                bsQuery.data.equity_lines.length === 0 &&
                bsQuery.data.current_earnings === "0.00") ? (
              <EmptyState
                title={t("reports.emptyTitle")}
                description={t("reports.emptyDesc")}
              />
            ) : (
              <div className="grid gap-6 lg:grid-cols-2">
                {/* ASSETS */}
                <div className="space-y-2">
                  <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                    {t("reports.assetsSection")}
                  </h2>
                  <table className="w-full text-left text-sm">
                    <tbody className="divide-y divide-border">
                      {bsQuery.data.asset_lines.map((line) => (
                        <tr key={line.account_id}>
                          <td className="w-24 py-2 font-mono text-xs">{line.code}</td>
                          <td className="py-2 font-medium">{line.name}</td>
                          <td className="py-2 text-right tabular-nums">
                            {formatBDT(line.amount, { banglaDigits })}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot className="border-t-2 border-border font-bold">
                      <tr>
                        <td colSpan={2} className="pt-3">
                          {t("reports.totalAssets")}
                        </td>
                        <td className="pt-3 text-right tabular-nums">
                          {formatBDT(bsQuery.data.total_assets, { banglaDigits })}
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                </div>

                {/* LIABILITIES + EQUITY */}
                <div className="space-y-4">
                  <div>
                    <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                      {t("reports.liabilitiesSection")}
                    </h2>
                    <table className="w-full text-left text-sm">
                      <tbody className="divide-y divide-border">
                        {bsQuery.data.liability_lines.map((line) => (
                          <tr key={line.account_id}>
                            <td className="w-24 py-2 font-mono text-xs">{line.code}</td>
                            <td className="py-2 font-medium">{line.name}</td>
                            <td className="py-2 text-right tabular-nums">
                              {formatBDT(line.amount, { banglaDigits })}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                      <tfoot className="border-t border-border font-semibold">
                        <tr>
                          <td colSpan={2} className="pt-2">
                            {t("reports.totalLiabilities")}
                          </td>
                          <td className="pt-2 text-right tabular-nums">
                            {formatBDT(bsQuery.data.total_liabilities, { banglaDigits })}
                          </td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>

                  <div>
                    <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                      {t("reports.equitySection")}
                    </h2>
                    <table className="w-full text-left text-sm">
                      <tbody className="divide-y divide-border">
                        {bsQuery.data.equity_lines.map((line) => (
                          <tr key={line.account_id}>
                            <td className="w-24 py-2 font-mono text-xs">{line.code}</td>
                            <td className="py-2 font-medium">{line.name}</td>
                            <td className="py-2 text-right tabular-nums">
                              {formatBDT(line.amount, { banglaDigits })}
                            </td>
                          </tr>
                        ))}
                        <tr>
                          <td className="w-24 py-2 font-mono text-xs">—</td>
                          <td className="py-2 font-medium">{t("reports.currentEarnings")}</td>
                          <td className="py-2 text-right tabular-nums">
                            {formatBDT(bsQuery.data.current_earnings, { banglaDigits })}
                          </td>
                        </tr>
                      </tbody>
                      <tfoot className="border-t-2 border-border font-bold">
                        <tr>
                          <td colSpan={2} className="pt-3">
                            {t("reports.totalLiabilitiesAndEquity")}
                          </td>
                          <td className="pt-3 text-right tabular-nums">
                            {formatBDT(bsQuery.data.total_liabilities_and_equity, { banglaDigits })}
                          </td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
