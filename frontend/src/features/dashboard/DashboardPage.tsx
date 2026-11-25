import { useQuery } from "@tanstack/react-query";
import { ArrowRight, BookOpen, FileSpreadsheet, Scale } from "lucide-react";
import type * as React from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { EmptyState } from "@/components/states/EmptyState";
import { ErrorState } from "@/components/states/ErrorState";
import { TableSkeleton } from "@/components/states/TableSkeleton";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { AccountItem, TrialBalanceResponse } from "@/features/accounting/types";
import { useAuthStore } from "@/features/auth/store";
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

  const accountsQuery = useQuery({
    queryKey: ["accounting", "accounts", "summary"],
    queryFn: ({ signal }) =>
      apiRequest<PaginatedResponse<AccountItem>>("/accounting/accounts?page=1&page_size=1", {
        accessToken,
        signal,
      }),
    enabled: Boolean(accessToken),
  });

  const tbQuery = useQuery({
    queryKey: ["accounting", "trial-balance", "summary"],
    queryFn: ({ signal }) =>
      apiRequest<TrialBalanceResponse>("/accounting/reports/trial-balance", {
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

  const accountTotal = accountsQuery.data?.meta.total ?? 0;

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

      <section className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {t("dashboard.accountsCount")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold tabular-nums">
              {banglaDigits ? toBanglaDigits(String(accountTotal)) : String(accountTotal)}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {t("dashboard.trialBalanceTotal")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold tabular-nums">
              {formatBDT(tbQuery.data?.grand_total_debit ?? "0.00", { banglaDigits })}
            </p>
          </CardContent>
        </Card>
      </section>

      <section aria-label={t("dashboard.quickActions")} className="grid gap-4 sm:grid-cols-3">
        {[
          { to: "/accounting/accounts", title: t("nav.accounts"), icon: BookOpen },
          { to: "/accounting/journals", title: t("nav.journals"), icon: FileSpreadsheet },
          { to: "/accounting/trial-balance", title: t("nav.trialBalance"), icon: Scale },
        ].map((item) => {
          const Icon = item.icon;
          return (
            <Link key={item.to} to={item.to} className="group block">
              <Card className="transition-colors group-hover:border-primary">
                <CardContent className="flex items-center justify-between p-5">
                  <div className="flex items-center gap-3">
                    <Icon className="h-5 w-5 text-primary" aria-hidden="true" />
                    <span className="font-semibold">{item.title}</span>
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
