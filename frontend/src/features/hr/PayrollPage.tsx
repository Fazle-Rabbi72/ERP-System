import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Info, CheckCircle2, FileText, Plus, Printer, X } from "lucide-react";
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
import type { AccountItem } from "@/features/accounting/types";
import { useAuthStore } from "@/features/auth/store";
import type {
  PaginatedPayrollRuns,
  PayrollRunDetail,
  PayrollRunItem,
} from "@/features/hr/types";
import { apiRequest } from "@/lib/api";
import { formatBDT } from "@/lib/format";

interface PaginatedAccounts {
  items: AccountItem[];
}

export function PayrollPage(): React.JSX.Element {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const accessToken = useAuthStore((s) => s.accessToken);
  const permissions = useAuthStore((s) => s.permissions);
  const banglaDigits = useAuthStore((s) => s.banglaDigits);

  const canWrite = permissions.includes("hr.payroll.write");
  const canPost = permissions.includes("hr.payroll.post");

  const now = new Date();
  const [showRunForm, setShowRunForm] = React.useState(false);
  const [payYear, setPayYear] = React.useState(String(now.getFullYear()));
  const [payMonth, setPayMonth] = React.useState(String(now.getMonth() + 1));
  const [notes, setNotes] = React.useState("");
  const [runError, setRunError] = React.useState<string | null>(null);

  const [selectedRunId, setSelectedRunId] = React.useState<string | null>(null);
  const [postingRun, setPostingRun] = React.useState<PayrollRunItem | null>(null);
  const [salaryExpenseAccId, setSalaryExpenseAccId] = React.useState("");
  const [paymentAccId, setPaymentAccId] = React.useState("");
  const [deductionsAccId, setDeductionsAccId] = React.useState("");
  const [postError, setPostError] = React.useState<string | null>(null);

  const runsQuery = useQuery({
    queryKey: ["hr", "payroll-runs"],
    queryFn: ({ signal }) =>
      apiRequest<PaginatedPayrollRuns>("/hr/payroll-runs?page=1&page_size=50", {
        accessToken,
        signal,
      }),
    enabled: Boolean(accessToken),
  });

  const detailQuery = useQuery({
    queryKey: ["hr", "payroll-run", selectedRunId],
    queryFn: ({ signal }) =>
      apiRequest<PayrollRunDetail>(`/hr/payroll-runs/${selectedRunId ?? ""}`, {
        accessToken,
        signal,
      }),
    enabled: Boolean(accessToken) && Boolean(selectedRunId),
  });

  const accountsQuery = useQuery({
    queryKey: ["accounting", "accounts", "payroll-select"],
    queryFn: ({ signal }) =>
      apiRequest<PaginatedAccounts>("/accounting/accounts?page=1&page_size=100", {
        accessToken,
        signal,
      }),
    enabled: Boolean(accessToken) && Boolean(postingRun),
  });

  const ledgerAccounts = (accountsQuery.data?.items ?? []).filter((a) => !a.is_group && a.is_active);

  const createRunMutation = useMutation({
    mutationFn: () =>
      apiRequest<PayrollRunDetail>("/hr/payroll-runs", {
        method: "POST",
        accessToken,
        body: {
          pay_year: Number(payYear),
          pay_month: Number(payMonth),
          notes: notes.trim(),
        },
      }),
    onSuccess: (created) => {
      setShowRunForm(false);
      setNotes("");
      setRunError(null);
      setSelectedRunId(created.id);
      void queryClient.invalidateQueries({ queryKey: ["hr", "payroll-runs"] });
    },
    onError: (err: Error) => {
      setRunError(err.message);
    },
  });

  const postRunMutation = useMutation({
    mutationFn: () =>
      apiRequest<PayrollRunItem>(`/hr/payroll-runs/${postingRun?.id ?? ""}/post`, {
        method: "POST",
        accessToken,
        body: {
          salary_expense_account_id: salaryExpenseAccId,
          payment_account_id: paymentAccId,
          deductions_payable_account_id: deductionsAccId || null,
        },
      }),
    onSuccess: () => {
      const postedId = postingRun?.id ?? null;
      setPostingRun(null);
      setPostError(null);
      void queryClient.invalidateQueries({ queryKey: ["hr", "payroll-runs"] });
      if (postedId) {
        void queryClient.invalidateQueries({ queryKey: ["hr", "payroll-run", postedId] });
      }
    },
    onError: (err: Error) => {
      setPostError(err.message);
    },
  });

  const handleCreateSubmit = (e: React.FormEvent): void => {
    e.preventDefault();
    setRunError(null);
    createRunMutation.mutate();
  };

  const handlePostSubmit = (e: React.FormEvent): void => {
    e.preventDefault();
    setPostError(null);
    postRunMutation.mutate();
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4 print:hidden">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{t("hr.payrollTitle")}</h1>
          <p className="text-sm text-muted-foreground">{t("hr.payrollSubtitle")}</p>
        </div>
        {canWrite ? (
          <Button
            size="sm"
            onClick={() => {
              setShowRunForm((v) => !v);
            }}
          >
            <Plus className="h-4 w-4" aria-hidden="true" />
            {t("hr.generatePayroll")}
          </Button>
        ) : null}
      </div>

      {showRunForm && canWrite ? (
        <Card className="print:hidden">
          <CardHeader>
            <CardTitle>{t("hr.generatePayroll")}</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleCreateSubmit} className="grid gap-4 sm:grid-cols-4">
              <div className="space-y-1">
                <Label htmlFor="pay-year">{t("hr.year")}</Label>
                <Input
                  id="pay-year"
                  type="number"
                  min="2020"
                  max="2100"
                  required
                  value={payYear}
                  onChange={(e) => {
                    setPayYear(e.target.value);
                  }}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="pay-month">{t("hr.month")}</Label>
                <Input
                  id="pay-month"
                  type="number"
                  min="1"
                  max="12"
                  required
                  value={payMonth}
                  onChange={(e) => {
                    setPayMonth(e.target.value);
                  }}
                />
              </div>
              <div className="space-y-1 sm:col-span-2">
                <Label htmlFor="pay-notes">{t("hr.notes")}</Label>
                <Input
                  id="pay-notes"
                  placeholder="Monthly salary disbursement..."
                  value={notes}
                  onChange={(e) => {
                    setNotes(e.target.value);
                  }}
                />
              </div>
              <div className="flex items-center justify-end gap-2 sm:col-span-4">
                {runError ? <p className="text-sm text-destructive">{runError}</p> : null}
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    setShowRunForm(false);
                  }}
                >
                  {t("accounting.cancel")}
                </Button>
                <Button type="submit" disabled={createRunMutation.isPending}>
                  {t("hr.runPayroll")}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      ) : null}

      {postingRun && canPost ? (
        <Card className="border-primary/40 print:hidden">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>
              {t("hr.postPayrollTitle")} — {postingRun.run_no}
            </CardTitle>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setPostingRun(null);
              }}
            >
              <X className="h-4 w-4" />
            </Button>
          </CardHeader>
          <CardContent>
            <form onSubmit={handlePostSubmit} className="grid gap-4 sm:grid-cols-3">
              <div className="space-y-1">
                <Label htmlFor="sal-exp-acc">{t("hr.salaryExpenseAccount")}</Label>
                <select
                  id="sal-exp-acc"
                  required
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={salaryExpenseAccId}
                  onChange={(e) => {
                    setSalaryExpenseAccId(e.target.value);
                  }}
                >
                  <option value="">-- Select --</option>
                  {ledgerAccounts.map((acc) => (
                    <option key={acc.id} value={acc.id}>
                      {acc.code} — {acc.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-1">
                <Label htmlFor="sal-pay-acc">{t("hr.paymentAccount")}</Label>
                <select
                  id="sal-pay-acc"
                  required
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={paymentAccId}
                  onChange={(e) => {
                    setPaymentAccId(e.target.value);
                  }}
                >
                  <option value="">-- Select --</option>
                  {ledgerAccounts.map((acc) => (
                    <option key={acc.id} value={acc.id}>
                      {acc.code} — {acc.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-1">
                <Label htmlFor="sal-ded-acc">{t("hr.deductionsAccount")}</Label>
                <select
                  id="sal-ded-acc"
                  required={Number(postingRun.total_deductions) > 0}
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={deductionsAccId}
                  onChange={(e) => {
                    setDeductionsAccId(e.target.value);
                  }}
                >
                  <option value="">-- Select --</option>
                  {ledgerAccounts.map((acc) => (
                    <option key={acc.id} value={acc.id}>
                      {acc.code} — {acc.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex items-center justify-end gap-2 sm:col-span-3">
                {postError ? <p className="text-sm text-destructive">{postError}</p> : null}
                <Button type="submit" disabled={postRunMutation.isPending}>
                  <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
                  {t("sales.postToGl")}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      ) : null}

      {/* Selected Payroll Run Payslips Detail */}
      {selectedRunId ? (
        <Card className="border-primary/40">
          <CardHeader className="flex flex-row items-center justify-between gap-2">
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-primary" aria-hidden="true" />
              {t("hr.payslipsTitle")} {detailQuery.data ? `— ${detailQuery.data.run_no}` : ""}
            </CardTitle>
            <div className="flex items-center gap-2 print:hidden">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  window.print();
                }}
              >
                <Printer className="h-4 w-4" aria-hidden="true" />
                {t("hr.printPayslips")}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                aria-label="Close payslips"
                onClick={() => {
                  setSelectedRunId(null);
                }}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {detailQuery.isLoading ? (
              <TableSkeleton rows={4} columns={7} />
            ) : detailQuery.isError ? (
              <ErrorState
                title={t("hr.payrollError")}
                message={detailQuery.error.message}
                retryLabel={t("dashboard.retry")}
                onRetry={() => void detailQuery.refetch()}
              />
            ) : detailQuery.data ? (
              <div className="space-y-4">
                <div
                  role="note"
                  className="flex items-start gap-3 rounded-lg border border-primary/20 bg-primary/5 p-3 text-xs text-foreground"
                >
                  <Info className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
                  <p>{detailQuery.data.advisory_note}</p>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="border-b border-border text-xs uppercase text-muted-foreground">
                      <tr>
                        <th className="pb-2 pr-3">{t("hr.employeeCode")}</th>
                        <th className="pb-2 pr-3">{t("hr.fullName")}</th>
                        <th className="pb-2 pr-3 text-right">{t("hr.basicSalary")}</th>
                        <th className="pb-2 pr-3 text-right">{t("hr.allowances")}</th>
                        <th className="pb-2 pr-3 text-right">{t("hr.grossSalary")}</th>
                        <th className="pb-2 pr-3 text-right">{t("hr.deductions")}</th>
                        <th className="pb-2 text-right">{t("hr.netSalary")}</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {detailQuery.data.lines.map((line) => (
                        <tr key={line.id}>
                          <td className="py-2 pr-3 font-mono text-xs">{line.employee_code}</td>
                          <td className="py-2 pr-3">
                            <div className="font-medium">{line.employee_name}</div>
                            {line.designation ? (
                              <div className="text-xs text-muted-foreground">
                                {line.designation}
                              </div>
                            ) : null}
                          </td>
                          <td className="py-2 pr-3 text-right tabular-nums">
                            {formatBDT(line.basic_salary, { banglaDigits })}
                          </td>
                          <td className="py-2 pr-3 text-right tabular-nums">
                            {formatBDT(line.allowances_total, { banglaDigits })}
                          </td>
                          <td className="py-2 pr-3 text-right tabular-nums">
                            {formatBDT(line.gross_salary, { banglaDigits })}
                          </td>
                          <td className="py-2 pr-3 text-right tabular-nums">
                            {formatBDT(line.total_deductions, { banglaDigits })}
                          </td>
                          <td className="py-2 text-right font-semibold tabular-nums">
                            {formatBDT(line.net_salary, { banglaDigits })}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot className="border-t-2 border-border font-bold">
                      <tr>
                        <td colSpan={4} className="pt-3 pr-3">
                          {t("accounting.grandTotal")}
                        </td>
                        <td className="pt-3 pr-3 text-right tabular-nums">
                          {formatBDT(detailQuery.data.total_gross, { banglaDigits })}
                        </td>
                        <td className="pt-3 pr-3 text-right tabular-nums">
                          {formatBDT(detailQuery.data.total_deductions, { banglaDigits })}
                        </td>
                        <td className="pt-3 text-right tabular-nums">
                          {formatBDT(detailQuery.data.total_net_pay, { banglaDigits })}
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              </div>
            ) : null}
          </CardContent>
        </Card>
      ) : null}

      <Card className="print:hidden">
        <CardHeader>
          <CardTitle>{t("hr.payrollRunsTitle")}</CardTitle>
        </CardHeader>
        <CardContent>
          {runsQuery.isLoading ? (
            <TableSkeleton rows={4} columns={6} />
          ) : runsQuery.isError ? (
            <ErrorState
              title={t("hr.payrollError")}
              message={runsQuery.error.message}
              retryLabel={t("dashboard.retry")}
              onRetry={() => void runsQuery.refetch()}
            />
          ) : !runsQuery.data || runsQuery.data.items.length === 0 ? (
            <EmptyState
              title={t("hr.payrollEmptyTitle")}
              description={t("hr.payrollEmptyDesc")}
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-border text-xs uppercase text-muted-foreground">
                  <tr>
                    <th className="pb-2 pr-4">{t("hr.runNo")}</th>
                    <th className="pb-2 pr-4">{t("hr.period")}</th>
                    <th className="pb-2 pr-4">{t("hr.status")}</th>
                    <th className="pb-2 pr-4 text-right">{t("hr.grossSalary")}</th>
                    <th className="pb-2 pr-4 text-right">{t("hr.deductions")}</th>
                    <th className="pb-2 pr-4 text-right">{t("hr.netSalary")}</th>
                    <th className="pb-2 text-right">{t("hr.actions")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {runsQuery.data.items.map((run) => (
                    <tr key={run.id}>
                      <td className="py-2.5 pr-4 font-mono text-xs">{run.run_no}</td>
                      <td className="py-2.5 pr-4">
                        {run.pay_year}-{String(run.pay_month).padStart(2, "0")}
                      </td>
                      <td className="py-2.5 pr-4">
                        <Badge variant={run.status === "posted" ? "default" : "secondary"}>
                          {run.status.toUpperCase()}
                        </Badge>
                      </td>
                      <td className="py-2.5 pr-4 text-right tabular-nums">
                        {formatBDT(run.total_gross, { banglaDigits })}
                      </td>
                      <td className="py-2.5 pr-4 text-right tabular-nums">
                        {formatBDT(run.total_deductions, { banglaDigits })}
                      </td>
                      <td className="py-2.5 pr-4 text-right font-semibold tabular-nums">
                        {formatBDT(run.total_net_pay, { banglaDigits })}
                      </td>
                      <td className="py-2.5 text-right">
                        <div className="flex justify-end gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              setSelectedRunId(run.id);
                            }}
                          >
                            {t("hr.viewPayslips")}
                          </Button>
                          {canPost && run.status === "draft" ? (
                            <Button
                              size="sm"
                              onClick={() => {
                                setPostingRun(run);
                              }}
                            >
                              {t("sales.postToGl")}
                            </Button>
                          ) : null}
                        </div>
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
