import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2 } from "lucide-react";
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
import type { AccountItem, JournalEntryItem } from "@/features/accounting/types";
import { useAuthStore } from "@/features/auth/store";
import { ApiError, apiRequest, type PaginatedResponse } from "@/lib/api";
import { formatBDT } from "@/lib/format";

interface DraftLine {
  key: string;
  account_id: string;
  description: string;
  debit: string;
  credit: string;
}

/** Parse a money string into integer poisha (cents) to avoid floating-point drift. */
function toPoisha(raw: string): number {
  const cleaned = raw.trim();
  if (!cleaned) return 0;
  const match = /^(\d+)(?:\.(\d{1,2}))?$/.exec(cleaned);
  if (!match) return 0;
  const taka = Number.parseInt(match[1] ?? "0", 10);
  const poisha = Number.parseInt((match[2] ?? "").padEnd(2, "0"), 10);
  return taka * 100 + poisha;
}

function poishaToDecimalString(poisha: number): string {
  const taka = Math.floor(poisha / 100);
  const rem = poisha % 100;
  return `${String(taka)}.${String(rem).padStart(2, "0")}`;
}

export function JournalsPage(): React.JSX.Element {
  const { t } = useTranslation();
  const accessToken = useAuthStore((s) => s.accessToken);
  const permissions = useAuthStore((s) => s.permissions);
  const banglaDigits = useAuthStore((s) => s.banglaDigits);
  const canWrite = permissions.includes("accounting.journals.write");
  const canPost = permissions.includes("accounting.journals.post");
  const queryClient = useQueryClient();

  const today = new Date().toISOString().slice(0, 10);
  const [entryDate, setEntryDate] = React.useState(today);
  const [reference, setReference] = React.useState("");
  const [narration, setNarration] = React.useState("");
  const [lines, setLines] = React.useState<DraftLine[]>([
    { key: "l1", account_id: "", description: "", debit: "", credit: "" },
    { key: "l2", account_id: "", description: "", debit: "", credit: "" },
  ]);
  const [formError, setFormError] = React.useState<string | null>(null);

  const accountsQuery = useQuery({
    queryKey: ["accounting", "accounts", "postable"],
    queryFn: ({ signal }) =>
      apiRequest<PaginatedResponse<AccountItem>>(
        "/accounting/accounts?page=1&page_size=100&sort_by=code&sort_dir=asc",
        { accessToken, signal },
      ),
    enabled: Boolean(accessToken),
  });

  const postableAccounts = React.useMemo(
    () => (accountsQuery.data?.items ?? []).filter((a) => !a.is_group && a.is_active),
    [accountsQuery.data],
  );

  const journalsQuery = useQuery({
    queryKey: ["accounting", "journals"],
    queryFn: ({ signal }) =>
      apiRequest<PaginatedResponse<JournalEntryItem>>(
        "/accounting/journals?page=1&page_size=25",
        { accessToken, signal },
      ),
    enabled: Boolean(accessToken),
  });

  const totalDebitPoisha = lines.reduce((acc, l) => acc + toPoisha(l.debit), 0);
  const totalCreditPoisha = lines.reduce((acc, l) => acc + toPoisha(l.credit), 0);
  const isBalanced = totalDebitPoisha > 0 && totalDebitPoisha === totalCreditPoisha;

  const createMutation = useMutation({
    mutationFn: () =>
      apiRequest<JournalEntryItem>("/accounting/journals", {
        method: "POST",
        accessToken,
        body: {
          entry_date: entryDate,
          reference,
          narration,
          lines: lines.map((l) => ({
            account_id: l.account_id,
            description: l.description,
            debit: poishaToDecimalString(toPoisha(l.debit)),
            credit: poishaToDecimalString(toPoisha(l.credit)),
          })),
        },
      }),
    onSuccess: () => {
      setFormError(null);
      setReference("");
      setNarration("");
      setLines([
        { key: `l-${String(Date.now())}-1`, account_id: "", description: "", debit: "", credit: "" },
        { key: `l-${String(Date.now())}-2`, account_id: "", description: "", debit: "", credit: "" },
      ]);
      void queryClient.invalidateQueries({ queryKey: ["accounting", "journals"] });
    },
    onError: (err: unknown) => {
      setFormError(err instanceof ApiError ? err.message : "Failed to save journal voucher.");
    },
  });

  const postMutation = useMutation({
    mutationFn: (entryId: string) =>
      apiRequest<JournalEntryItem>(`/accounting/journals/${entryId}/post`, {
        method: "POST",
        accessToken,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["accounting"] });
    },
  });

  const reverseMutation = useMutation({
    mutationFn: (entryId: string) =>
      apiRequest<JournalEntryItem>(`/accounting/journals/${entryId}/reverse`, {
        method: "POST",
        accessToken,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["accounting"] });
    },
  });

  const updateLine = (key: string, patch: Partial<DraftLine>): void => {
    setLines((prev) => prev.map((l) => (l.key === key ? { ...l, ...patch } : l)));
  };

  const handleSubmit = (e: React.FormEvent): void => {
    e.preventDefault();
    setFormError(null);
    if (!narration.trim()) {
      setFormError("Narration is required.");
      return;
    }
    if (lines.some((l) => !l.account_id)) {
      setFormError("Please select an account for every line.");
      return;
    }
    if (!isBalanced) {
      setFormError("Total Debit must equal Total Credit and be greater than zero.");
      return;
    }
    createMutation.mutate();
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{t("accounting.journalsTitle")}</h1>
        <p className="text-sm text-muted-foreground">{t("accounting.journalsSubtitle")}</p>
      </div>

      {canWrite ? (
        <Card>
          <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2">
            <CardTitle>{t("accounting.newJournal")}</CardTitle>
            <Badge variant={isBalanced ? "default" : "secondary"}>
              {isBalanced ? t("accounting.balanced") : t("accounting.outOfBalance")}
            </Badge>
          </CardHeader>
          <CardContent>
            {formError ? (
              <div role="alert" className="mb-4 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {formError}
              </div>
            ) : null}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-3">
                <div className="space-y-1">
                  <Label htmlFor="jv_date">{t("accounting.entryDate")}</Label>
                  <Input
                    id="jv_date"
                    type="date"
                    value={entryDate}
                    onChange={(e) => { setEntryDate(e.target.value); }}
                  />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="jv_ref">{t("accounting.reference")}</Label>
                  <Input
                    id="jv_ref"
                    placeholder="INV-2026-001"
                    value={reference}
                    onChange={(e) => { setReference(e.target.value); }}
                  />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="jv_narr">{t("accounting.narration")}</Label>
                  <Input
                    id="jv_narr"
                    placeholder="Cash sale / Office rent payment"
                    value={narration}
                    onChange={(e) => { setNarration(e.target.value); }}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label>{t("accounting.lines")}</Label>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setLines((prev) => [
                        ...prev,
                        {
                          key: `l-${String(Date.now())}-${String(prev.length)}`,
                          account_id: "",
                          description: "",
                          debit: "",
                          credit: "",
                        },
                      ]);
                    }}
                  >
                    <Plus className="h-4 w-4" aria-hidden="true" />
                    {t("accounting.addLine")}
                  </Button>
                </div>

                {lines.map((line) => (
                  <div key={line.key} className="grid gap-2 sm:grid-cols-12">
                    <select
                      aria-label="Account"
                      className="h-10 rounded-md border border-input bg-card px-2 text-sm sm:col-span-4"
                      value={line.account_id}
                      onChange={(e) => { updateLine(line.key, { account_id: e.target.value }); }}
                    >
                      <option value="">-- Select Ledger Account --</option>
                      {postableAccounts.map((acc) => (
                        <option key={acc.id} value={acc.id}>
                          {acc.code} — {acc.name}
                        </option>
                      ))}
                    </select>
                    <Input
                      className="sm:col-span-3"
                      placeholder="Line note"
                      value={line.description}
                      onChange={(e) => { updateLine(line.key, { description: e.target.value }); }}
                    />
                    <Input
                      className="sm:col-span-2"
                      inputMode="decimal"
                      placeholder={t("accounting.debit")}
                      value={line.debit}
                      onChange={(e) => {
                        updateLine(line.key, { debit: e.target.value, credit: "" });
                      }}
                    />
                    <Input
                      className="sm:col-span-2"
                      inputMode="decimal"
                      placeholder={t("accounting.credit")}
                      value={line.credit}
                      onChange={(e) => {
                        updateLine(line.key, { credit: e.target.value, debit: "" });
                      }}
                    />
                    <div className="flex items-center justify-end sm:col-span-1">
                      {lines.length > 2 ? (
                        <Button
                          variant="ghost"
                          size="sm"
                          aria-label="Remove line"
                          onClick={() => {
                            setLines((prev) => prev.filter((item) => item.key !== line.key));
                          }}
                        >
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      ) : null}
                    </div>
                  </div>
                ))}
              </div>

              <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-3">
                <div className="flex gap-6 text-sm font-medium tabular-nums">
                  <span>
                    {t("accounting.totalDebit")}:{" "}
                    {formatBDT(poishaToDecimalString(totalDebitPoisha), { banglaDigits })}
                  </span>
                  <span>
                    {t("accounting.totalCredit")}:{" "}
                    {formatBDT(poishaToDecimalString(totalCreditPoisha), { banglaDigits })}
                  </span>
                </div>
                <Button type="submit" disabled={!isBalanced || createMutation.isPending}>
                  {t("accounting.createDraft")}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>{t("accounting.journalsTitle")}</CardTitle>
        </CardHeader>
        <CardContent>
          {journalsQuery.isLoading ? (
            <TableSkeleton rows={5} columns={5} />
          ) : journalsQuery.isError ? (
            <ErrorState
              title={t("accounting.journalsErrorTitle")}
              message={journalsQuery.error.message}
              retryLabel={t("dashboard.retry")}
              onRetry={() => void journalsQuery.refetch()}
            />
          ) : !journalsQuery.data || journalsQuery.data.items.length === 0 ? (
            <EmptyState
              title={t("accounting.journalsEmptyTitle")}
              description={t("accounting.journalsEmptyDesc")}
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-border text-xs uppercase text-muted-foreground">
                  <tr>
                    <th className="pb-2 pr-4">Voucher</th>
                    <th className="pb-2 pr-4">{t("accounting.entryDate")}</th>
                    <th className="pb-2 pr-4">{t("accounting.narration")}</th>
                    <th className="pb-2 pr-4 text-right">Amount</th>
                    <th className="pb-2 pr-4">Status</th>
                    <th className="pb-2 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {journalsQuery.data.items.map((entry) => {
                    const total = entry.lines.reduce((sum, l) => sum + toPoisha(l.debit), 0);
                    return (
                      <tr key={entry.id}>
                        <td className="py-3 pr-4 font-mono text-xs font-medium">{entry.voucher_no}</td>
                        <td className="py-3 pr-4 tabular-nums">{entry.entry_date}</td>
                        <td className="py-3 pr-4">{entry.narration}</td>
                        <td className="py-3 pr-4 text-right tabular-nums">
                          {formatBDT(poishaToDecimalString(total), { banglaDigits })}
                        </td>
                        <td className="py-3 pr-4">
                          <Badge variant={entry.status === "posted" ? "default" : "secondary"}>
                            {entry.status.toUpperCase()}
                          </Badge>
                        </td>
                        <td className="py-3 text-right">
                          {canPost && entry.status === "draft" ? (
                            <Button
                              size="sm"
                              disabled={postMutation.isPending}
                              onClick={() => { postMutation.mutate(entry.id); }}
                            >
                              {t("accounting.post")}
                            </Button>
                          ) : null}
                          {canPost && entry.status === "posted" ? (
                            <Button
                              variant="outline"
                              size="sm"
                              disabled={reverseMutation.isPending}
                              onClick={() => { reverseMutation.mutate(entry.id); }}
                            >
                              {t("accounting.reverse")}
                            </Button>
                          ) : null}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
