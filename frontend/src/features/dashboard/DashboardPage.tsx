import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowRight,
  Banknote,
  BarChart3,
  FileCheck2,
  Receipt,
  ShoppingCart,
  Users,
  Warehouse,
} from "lucide-react";
import type * as React from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { EmptyState } from "@/components/states/EmptyState";
import { ErrorState } from "@/components/states/ErrorState";
import { TableSkeleton } from "@/components/states/TableSkeleton";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuthStore } from "@/features/auth/store";
import type { DashboardSummary } from "@/features/reports/types";
import { apiRequest, type PaginatedResponse } from "@/lib/api";
import { formatBDT, toBanglaDigits } from "@/lib/format";

interface RoleItem {
  id: string;
  code: string;
  name: string;
  description: string;
  is_system: boolean;
}

export function DashboardPage(): React.JSX.Element {
  const { t } = useTranslation();
  const user = useAuthStore((s) => s.user);
  const accessToken = useAuthStore((s) => s.accessToken);
  const banglaDigits = useAuthStore((s) => s.banglaDigits);

  const summaryQuery = useQuery({
    queryKey: ["reports", "dashboard-summary"],
    queryFn: ({ signal }) =>
      apiRequest<DashboardSummary>("/reports/dashboard-summary", {
        accessToken,
        signal,
      }),
    enabled: Boolean(accessToken),
  });

  const rolesQuery = useQuery({
    queryKey: ["rbac", "roles"],
    queryFn: ({ signal }) =>
      apiRequest<PaginatedResponse<RoleItem>>("/rbac/roles?page=1&page_size=20", {
        accessToken,
        signal,
      }),
    enabled: Boolean(accessToken),
  });

  const summary = summaryQuery.data;
  const revNum = Number(summary?.total_revenue ?? 0);
  const expNum = Number(summary?.total_expense ?? 0);
  const totalFlow = revNum + expNum;
  const revPct = totalFlow > 0 ? Math.round((revNum / totalFlow) * 100) : 0;

  const fmtCount = (n: number): string => (banglaDigits ? toBanglaDigits(String(n)) : String(n));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          {t("dashboard.title")}
        </h1>
        <p className="text-sm text-muted-foreground">
          {t("dashboard.welcome")}, {user?.full_name ?? ""} ({user?.email ?? ""})
        </p>
      </div>

      {/* Executive Financial KPIs */}
      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {t("reports.totalRevenue")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold tabular-nums text-emerald-700">
              {formatBDT(summary?.total_revenue ?? "0.00", { banglaDigits })}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {t("reports.totalExpense")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold tabular-nums">
              {formatBDT(summary?.total_expense ?? "0.00", { banglaDigits })}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {t("reports.netProfit")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold tabular-nums text-primary">
              {formatBDT(summary?.net_profit ?? "0.00", { banglaDigits })}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {t("reports.totalAssets")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold tabular-nums">
              {formatBDT(summary?.total_assets ?? "0.00", { banglaDigits })}
            </p>
          </CardContent>
        </Card>
      </section>

      {/* Operational KPIs across Sales, Purchase, HR, Inventory */}
      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium uppercase text-muted-foreground">
              {t("dashboard.arDue")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xl font-bold tabular-nums">
              {formatBDT(summary?.accounts_receivable_due ?? "0.00", { banglaDigits })}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium uppercase text-muted-foreground">
              {t("dashboard.apDue")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xl font-bold tabular-nums">
              {formatBDT(summary?.accounts_payable_due ?? "0.00", { banglaDigits })}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-1.5 text-xs font-medium uppercase text-muted-foreground">
              <Users className="h-3.5 w-3.5" aria-hidden="true" />
              {t("dashboard.activeEmployees")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xl font-bold tabular-nums">
              {fmtCount(summary?.active_employees_count ?? 0)}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-1.5 text-xs font-medium uppercase text-muted-foreground">
              <AlertTriangle className="h-3.5 w-3.5 text-amber-600" aria-hidden="true" />
              {t("inventory.lowStockAlerts")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xl font-bold tabular-nums">
              {fmtCount(summary?.low_stock_products_count ?? 0)}
            </p>
          </CardContent>
        </Card>
      </section>

      {/* Revenue vs Expense Visual Ratio */}
      {totalFlow > 0 ? (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">{t("dashboard.revenueVsExpense")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex h-3 w-full overflow-hidden rounded-full bg-secondary">
              <div
                className="bg-emerald-600 transition-all"
                style={{ width: `${String(revPct)}%` }}
              />
              <div
                className="bg-rose-500 transition-all"
                style={{ width: `${String(100 - revPct)}%` }}
              />
            </div>
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>
                {t("reports.totalRevenue")}: {revPct}%
              </span>
              <span>
                {t("reports.totalExpense")}: {100 - revPct}%
              </span>
            </div>
          </CardContent>
        </Card>
      ) : null}

      {/* ERP Quick Actions */}
      <section aria-label={t("dashboard.quickActions")} className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {[
          { to: "/reports/statements", title: t("nav.financialStatements"), icon: BarChart3 },
          { to: "/sales/invoices", title: t("nav.invoices"), icon: Receipt },
          { to: "/purchase/bills", title: t("nav.bills"), icon: ShoppingCart },
          { to: "/inventory/stock", title: t("nav.stock"), icon: Warehouse },
          { to: "/vat/mushak", title: t("nav.vatMushak"), icon: FileCheck2 },
          { to: "/hr/payroll", title: t("nav.payroll"), icon: Banknote },
        ].map((item) => {
          const Icon = item.icon;
          return (
            <Link key={item.to} to={item.to} className="group block">
              <Card className="transition-colors group-hover:border-primary">
                <CardContent className="flex items-center justify-between p-4">
                  <div className="flex items-center gap-3">
                    <Icon className="h-5 w-5 text-primary" aria-hidden="true" />
                    <span className="text-sm font-semibold">{item.title}</span>
                  </div>
                  <ArrowRight className="h-4 w-4 text-muted-foreground transition-transform group-hover:translate-x-1" />
                </CardContent>
              </Card>
            </Link>
          );
        })}
      </section>

      <Card>
        <CardHeader>
          <CardTitle>{t("dashboard.rolesTitle")}</CardTitle>
        </CardHeader>
        <CardContent>
          {rolesQuery.isLoading ? (
            <TableSkeleton rows={4} columns={3} />
          ) : rolesQuery.isError ? (
            <ErrorState
              title={t("dashboard.rolesErrorTitle")}
              message={rolesQuery.error.message}
              retryLabel={t("dashboard.retry")}
              onRetry={() => void rolesQuery.refetch()}
            />
          ) : !rolesQuery.data || rolesQuery.data.items.length === 0 ? (
            <EmptyState
              title={t("dashboard.rolesEmptyTitle")}
              description={t("dashboard.rolesEmptyDesc")}
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-border text-xs uppercase text-muted-foreground">
                  <tr>
                    <th className="pb-2 pr-4">Code</th>
                    <th className="pb-2 pr-4">Name</th>
                    <th className="pb-2">Type</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {rolesQuery.data.items.map((role) => (
                    <tr key={role.id}>
                      <td className="py-3 pr-4 font-mono text-xs">{role.code}</td>
                      <td className="py-3 pr-4 font-medium">{role.name}</td>
                      <td className="py-3">
                        <Badge variant={role.is_system ? "default" : "secondary"}>
                          {role.is_system ? t("dashboard.systemRole") : t("dashboard.customRole")}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
