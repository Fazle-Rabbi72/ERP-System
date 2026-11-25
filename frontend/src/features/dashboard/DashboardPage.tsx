import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  Banknote,
  BarChart3,
  FileCheck2,
  PackageSearch,
  Receipt,
  Scale,
  ShoppingCart,
  TrendingDown,
  TrendingUp,
  Users,
  Wallet,
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
import { Skeleton } from "@/components/ui/skeleton";
import { StatCard } from "@/components/ui/stat-card";
import { useAuthStore } from "@/features/auth/store";
import { DashboardCharts } from "@/features/dashboard/DashboardCharts";
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
  const money = (value: string | undefined): string => formatBDT(value ?? "0.00", { banglaDigits });
  const count = (n: number | undefined): string => {
    const text = String(n ?? 0);
    return banglaDigits ? toBanglaDigits(text) : text;
  };

  const shortcuts = [
    { to: "/reports/statements", title: t("nav.financialStatements"), icon: BarChart3 },
    { to: "/sales/invoices", title: t("nav.invoices"), icon: Receipt },
    { to: "/purchase/bills", title: t("nav.bills"), icon: ShoppingCart },
    { to: "/inventory/stock", title: t("nav.stock"), icon: Warehouse },
    { to: "/vat/mushak", title: t("nav.vatMushak"), icon: FileCheck2 },
    { to: "/hr/payroll", title: t("nav.payroll"), icon: Banknote },
  ];

  return (
    <div className="space-y-6 sm:space-y-8">
      <div>
        <h1 className="text-foreground">{t("dashboard.title")}</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {t("dashboard.welcome")}, {user?.full_name ?? ""}
        </p>
      </div>

      {summaryQuery.isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Card key={i} className="p-5">
              <Skeleton className="h-3.5 w-24" />
              <Skeleton className="mt-3 h-7 w-36" />
            </Card>
          ))}
        </div>
      ) : summaryQuery.isError ? (
        <ErrorState
          title={t("reports.loadError")}
          message={summaryQuery.error.message}
          retryLabel={t("dashboard.retry")}
          onRetry={() => void summaryQuery.refetch()}
        />
      ) : (
        <>
          <section aria-label={t("dashboard.financialOverview")} className="space-y-3">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              {t("dashboard.financialOverview")}
            </h2>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <StatCard
                label={t("reports.totalRevenue")}
                value={money(summary?.total_revenue)}
                icon={TrendingUp}
              />
              <StatCard
                label={t("reports.totalExpense")}
                value={money(summary?.total_expense)}
                icon={TrendingDown}
              />
              <StatCard
                label={t("reports.netProfit")}
                value={money(summary?.net_profit)}
                icon={Scale}
                emphasis
              />
              <StatCard
                label={t("reports.totalAssets")}
                value={money(summary?.total_assets)}
                icon={Wallet}
              />
            </div>
          </section>

          {summary ? <DashboardCharts summary={summary} banglaDigits={banglaDigits} /> : null}

          <section aria-label={t("dashboard.operations")} className="space-y-3">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              {t("dashboard.operations")}
            </h2>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <StatCard
                label={t("dashboard.arDue")}
                value={money(summary?.accounts_receivable_due)}
                icon={Receipt}
              />
              <StatCard
                label={t("dashboard.apDue")}
                value={money(summary?.accounts_payable_due)}
                icon={ShoppingCart}
              />
              <StatCard
                label={t("dashboard.activeEmployees")}
                value={count(summary?.active_employees_count)}
                icon={Users}
              />
              <StatCard
                label={t("inventory.lowStockAlerts")}
                value={count(summary?.low_stock_products_count)}
                icon={PackageSearch}
              />
            </div>
          </section>
        </>
      )}

      <section aria-label={t("dashboard.quickActions")} className="space-y-3">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          {t("dashboard.quickActions")}
        </h2>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {shortcuts.map((item) => {
            const Icon = item.icon;
            return (
              <Link key={item.to} to={item.to} className="group block">
                <Card className="transition-all duration-150 group-hover:-translate-y-0.5 group-hover:border-primary/40 group-hover:shadow-md">
                  <CardContent className="flex items-center justify-between p-4 pt-4">
                    <div className="flex items-center gap-3">
                      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                        <Icon className="h-[18px] w-[18px]" aria-hidden="true" />
                      </span>
                      <span className="text-sm font-medium">{item.title}</span>
                    </div>
                    <ArrowRight className="h-4 w-4 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-primary" />
                  </CardContent>
                </Card>
              </Link>
            );
          })}
        </div>
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
                <thead>
                  <tr>
                    <th>Code</th>
                    <th>Name</th>
                    <th>Type</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {rolesQuery.data.items.map((role) => (
                    <tr key={role.id}>
                      <td className="font-mono text-xs">{role.code}</td>
                      <td className="font-medium">{role.name}</td>
                      <td>
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
