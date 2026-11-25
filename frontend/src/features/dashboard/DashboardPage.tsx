import { useQuery } from "@tanstack/react-query";
import { Building2, Languages, LogOut } from "lucide-react";
import type * as React from "react";
import { useTranslation } from "react-i18next";

import { EmptyState } from "@/components/states/EmptyState";
import { ErrorState } from "@/components/states/ErrorState";
import { TableSkeleton } from "@/components/states/TableSkeleton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuthStore } from "@/features/auth/store";
import { apiRequest, type PaginatedResponse } from "@/lib/api";
import { formatBDT } from "@/lib/format";

interface RoleItem {
  id: string;
  code: string;
  name: string;
  description: string;
  is_system: boolean;
}

export function DashboardPage(): React.JSX.Element {
  const { t, i18n } = useTranslation();
  const user = useAuthStore((s) => s.user);
  const accessToken = useAuthStore((s) => s.accessToken);
  const banglaDigits = useAuthStore((s) => s.banglaDigits);
  const toggleBanglaDigits = useAuthStore((s) => s.toggleBanglaDigits);
  const logout = useAuthStore((s) => s.logout);

  const rolesQuery = useQuery({
    queryKey: ["rbac", "roles"],
    queryFn: ({ signal }) =>
      apiRequest<PaginatedResponse<RoleItem>>("/rbac/roles?page=1&page_size=20", {
        accessToken,
        signal,
      }),
    enabled: Boolean(accessToken),
  });

  const toggleLanguage = (): void => {
    void i18n.changeLanguage(i18n.language === "bn" ? "en" : "bn");
  };

  return (
    <div className="min-h-screen bg-background">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-primary focus:px-3 focus:py-2 focus:text-primary-foreground"
      >
        {t("app.skipToContent")}
      </a>

      <header className="border-b border-border bg-card">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 sm:px-6">
          <div className="flex items-center gap-2 text-primary">
            <Building2 className="h-5 w-5" aria-hidden="true" />
            <span className="font-bold">{t("app.name")}</span>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={toggleBanglaDigits}>
              {t("app.banglaDigits")}: {banglaDigits ? "চালু" : "Off"}
            </Button>
            <Button variant="outline" size="sm" onClick={toggleLanguage}>
              <Languages className="h-4 w-4" aria-hidden="true" />
              {i18n.language === "bn" ? "English" : "বাংলা"}
            </Button>
            <Button variant="ghost" size="sm" onClick={() => void logout()}>
              <LogOut className="h-4 w-4" aria-hidden="true" />
              {t("app.logout")}
            </Button>
          </div>
        </div>
      </header>

      <main id="main-content" className="mx-auto max-w-6xl space-y-6 px-4 py-6 sm:px-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            {t("dashboard.title")}
          </h1>
          <p className="text-sm text-muted-foreground">
            {t("dashboard.welcome")}, {user?.full_name ?? ""} ({user?.email ?? ""})
          </p>
        </div>

        <section aria-label={t("dashboard.sampleMetrics")} className="grid gap-4 sm:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {t("dashboard.cashBalance")}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold tabular-nums">
                {formatBDT("12540850.75", { banglaDigits })}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {t("dashboard.monthlySales")}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold tabular-nums">
                {formatBDT("3485200.00", { banglaDigits })}
              </p>
            </CardContent>
          </Card>
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
      </main>
    </div>
  );
}
