import { useQuery } from "@tanstack/react-query";
import * as React from "react";
import { useTranslation } from "react-i18next";

import { EmptyState } from "@/components/states/EmptyState";
import { ErrorState } from "@/components/states/ErrorState";
import { TableSkeleton } from "@/components/states/TableSkeleton";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { TrialBalanceResponse } from "@/features/accounting/types";
import { useAuthStore } from "@/features/auth/store";
import { apiRequest } from "@/lib/api";
import { formatBDT } from "@/lib/format";

export function TrialBalancePage(): React.JSX.Element {
  const { t } = useTranslation();
  const accessToken = useAuthStore((s) => s.accessToken);
  const banglaDigits = useAuthStore((s) => s.banglaDigits);
  const [asOfDate, setAsOfDate] = React.useState("");

  const queryStr = asOfDate ? `?as_of_date=${encodeURIComponent(asOfDate)}` : "";
  const tbQuery = useQuery({
    queryKey: ["accounting", "trial-balance", asOfDate],
    queryFn: ({ signal }) =>
      apiRequest<TrialBalanceResponse>(`/accounting/reports/trial-balance${queryStr}`, {
        accessToken,
        signal,
      }),
    enabled: Boolean(accessToken),
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{t("accounting.trialBalanceTitle")}</h1>
          <p className="text-sm text-muted-foreground">{t("accounting.trialBalanceSubtitle")}</p>
        </div>
        <div className="space-y-1">
          <Label htmlFor="as_of_date">{t("accounting.asOfDate")}</Label>
          <Input
            id="as_of_date"
            type="date"
            value={asOfDate}
            onChange={(e) => { setAsOfDate(e.target.value); }}
          />
        </div>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>{t("accounting.trialBalanceTitle")}</CardTitle>
          {tbQuery.data ? (
            <Badge variant={tbQuery.data.is_balanced ? "default" : "secondary"}>
              {tbQuery.data.is_balanced ? t("accounting.balanced") : t("accounting.outOfBalance")}
            </Badge>
          ) : null}
        </CardHeader>
        <CardContent>
          {tbQuery.isLoading ? (
            <TableSkeleton rows={5} columns={5} />
          ) : tbQuery.isError ? (
            <ErrorState
              title={t("accounting.trialBalanceErrorTitle")}
              message={tbQuery.error.message}
              retryLabel={t("dashboard.retry")}
              onRetry={() => void tbQuery.refetch()}
            />
          ) : !tbQuery.data || tbQuery.data.rows.length === 0 ? (
            <EmptyState
              title={t("accounting.trialBalanceEmptyTitle")}
              description={t("accounting.trialBalanceEmptyDesc")}
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-border text-xs uppercase text-muted-foreground">
                  <tr>
                    <th className="pb-2 pr-4">{t("accounting.code")}</th>
                    <th className="pb-2 pr-4">{t("accounting.name")}</th>
                    <th className="pb-2 pr-4 text-right">{t("accounting.totalDebit")}</th>
                    <th className="pb-2 pr-4 text-right">{t("accounting.totalCredit")}</th>
                    <th className="pb-2 pr-4 text-right">{t("accounting.netDebit")}</th>
                    <th className="pb-2 text-right">{t("accounting.netCredit")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {tbQuery.data.rows.map((row) => (
                    <tr key={row.account_id}>
                      <td className="py-2.5 pr-4 font-mono text-xs">{row.code}</td>
                      <td className="py-2.5 pr-4 font-medium">{row.name}</td>
                      <td className="py-2.5 pr-4 text-right tabular-nums">
                        {formatBDT(row.total_debit, { banglaDigits })}
                      </td>
                      <td className="py-2.5 pr-4 text-right tabular-nums">
                        {formatBDT(row.total_credit, { banglaDigits })}
                      </td>
                      <td className="py-2.5 pr-4 text-right tabular-nums">
                        {formatBDT(row.net_debit, { banglaDigits })}
                      </td>
                      <td className="py-2.5 text-right tabular-nums">
                        {formatBDT(row.net_credit, { banglaDigits })}
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot className="border-t-2 border-border font-bold">
                  <tr>
                    <td colSpan={2} className="pt-3 pr-4">
                      {t("accounting.grandTotal")}
                    </td>
                    <td className="pt-3 pr-4 text-right tabular-nums">
                      {formatBDT(tbQuery.data.grand_total_debit, { banglaDigits })}
                    </td>
                    <td className="pt-3 pr-4 text-right tabular-nums">
                      {formatBDT(tbQuery.data.grand_total_credit, { banglaDigits })}
                    </td>
                    <td colSpan={2} />
                  </tr>
                </tfoot>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
