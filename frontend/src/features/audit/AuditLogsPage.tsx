import { useQuery } from "@tanstack/react-query";
import type * as React from "react";
import { useTranslation } from "react-i18next";

import { EmptyState } from "@/components/states/EmptyState";
import { ErrorState } from "@/components/states/ErrorState";
import { TableSkeleton } from "@/components/states/TableSkeleton";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuthStore } from "@/features/auth/store";
import { apiRequest, type PaginatedResponse } from "@/lib/api";

interface AuditLogItem {
  id: string;
  action: string;
  resource_type: string;
  resource_id: string | null;
  request_id: string | null;
  created_at: string;
}

export function AuditLogsPage(): React.JSX.Element {
  const { t } = useTranslation();
  const accessToken = useAuthStore((s) => s.accessToken);

  const logsQuery = useQuery({
    queryKey: ["audit", "logs"],
    queryFn: ({ signal }) =>
      apiRequest<PaginatedResponse<AuditLogItem>>("/audit-logs?page=1&page_size=25", {
        accessToken,
        signal,
      }),
    enabled: Boolean(accessToken),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{t("audit.title")}</h1>
        <p className="text-sm text-muted-foreground">{t("audit.subtitle")}</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t("audit.title")}</CardTitle>
        </CardHeader>
        <CardContent>
          {logsQuery.isLoading ? (
            <TableSkeleton rows={6} columns={4} />
          ) : logsQuery.isError ? (
            <ErrorState
              title={t("audit.errorTitle")}
              message={logsQuery.error.message}
              retryLabel={t("dashboard.retry")}
              onRetry={() => void logsQuery.refetch()}
            />
          ) : !logsQuery.data || logsQuery.data.items.length === 0 ? (
            <EmptyState title={t("audit.emptyTitle")} description={t("audit.emptyDesc")} />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-border text-xs uppercase text-muted-foreground">
                  <tr>
                    <th className="pb-2 pr-4">{t("audit.time")}</th>
                    <th className="pb-2 pr-4">{t("audit.action")}</th>
                    <th className="pb-2 pr-4">{t("audit.resource")}</th>
                    <th className="pb-2">{t("audit.requestId")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {logsQuery.data.items.map((log) => (
                    <tr key={log.id}>
                      <td className="py-2.5 pr-4 tabular-nums text-xs">
                        {new Date(log.created_at).toLocaleString()}
                      </td>
                      <td className="py-2.5 pr-4">
                        <Badge variant="default">{log.action}</Badge>
                      </td>
                      <td className="py-2.5 pr-4 font-mono text-xs">
                        {log.resource_type}
                        {log.resource_id ? `:${log.resource_id.slice(0, 8)}` : ""}
                      </td>
                      <td className="py-2.5 font-mono text-xs text-muted-foreground">
                        {log.request_id ?? "—"}
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
