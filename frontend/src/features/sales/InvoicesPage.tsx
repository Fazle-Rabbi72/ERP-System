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
import type { AccountItem } from "@/features/accounting/types";
import { useAuthStore } from "@/features/auth/store";
import type {
  CustomerItem,
  CustomerPaymentItem,
  PaymentMethod,
  SalesInvoiceItem,
} from "@/features/sales/types";
import { ApiError, apiRequest, type PaginatedResponse } from "@/lib/api";
import { formatBDT } from "@/lib/format";

interface DraftInvLine {
  key: string;
  description: string;
  quantity: string;
  unit_price: string;
  vat_rate_percent: string;
}

function parsePoisha(raw: string): number {
  const m = /^(\d+)(?:\.(\d{1,2}))?$/.exec(raw.trim());
  if (!m) return 0;
  return Number.parseInt(m[1] ?? "0", 10) * 100 + Number.parseInt((m[2] ?? "").padEnd(2, "0"), 10);
}

function poishaToStr(poisha: number): string {
  const safe = Math.max(0, Math.round(poisha));
  return `${String(Math.floor(safe / 100))}.${String(safe % 100).padStart(2, "0")}`;
}

export function InvoicesPage(): React.JSX.Element {
  const { t } = useTranslation();
  const accessToken = useAuthStore((s) => s.accessToken);
  const permissions = useAuthStore((s) => s.permissions);
  const banglaDigits = useAuthStore((s) => s.banglaDigits);
  const canWrite = permissions.includes("sales.invoices.write");
  const canPost = permissions.includes("sales.invoices.post");
  const canPay = permissions.includes("sales.payments.write");
  const queryClient = useQueryClient();

  const today = new Date().toISOString().slice(0, 10);
  const [customerId, setCustomerId] = React.useState("");
  const [invoiceDate, setInvoiceDate] = React.useState(today);
  const [dueDate, setDueDate] = React.useState(today);
  const [lines, setLines] = React.useState<DraftInvLine[]>([
    { key: "il-1", description: "", quantity: "1", unit_price: "", vat_rate_percent: "0.00" },
  ]);
  const [formError, setFormError] = React.useState<string | null>(null);

  // Payment modal/panel state
  const [payingInvoice, setPayingInvoice] = React.useState<SalesInvoiceItem | null>(null);
  const [payAmount, setPayAmount] = React.useState("");
  const [payMethod, setPayMethod] = React.useState<PaymentMethod>("cash");
  const [depositAccountId, setDepositAccountId] = React.useState("");
  const [payError, setPayError] = React.useState<string | null>(null);

  const customersQuery = useQuery({
    queryKey: ["sales", "customers", "dropdown"],
    queryFn: ({ signal }) =>
      apiRequest<PaginatedResponse<CustomerItem>>("/sales/customers?page=1&page_size=100", {
        accessToken,
        signal,
      }),
    enabled: Boolean(accessToken),
  });

  const accountsQuery = useQuery({
    queryKey: ["accounting", "accounts", "deposit"],
    queryFn: ({ signal }) =>
      apiRequest<PaginatedResponse<AccountItem>>(
        "/accounting/accounts?page=1&page_size=100&account_type=asset",
        { accessToken, signal },
      ),
    enabled: Boolean(accessToken),
  });

  const depositAccounts = React.useMemo(
    () => (accountsQuery.data?.items ?? []).filter((a) => !a.is_group && a.is_active),
    [accountsQuery.data],
  );

  const invoicesQuery = useQuery({
    queryKey: ["sales", "invoices"],
    queryFn: ({ signal }) =>
      apiRequest<PaginatedResponse<SalesInvoiceItem>>("/sales/invoices?page=1&page_size=25", {
        accessToken,
        signal,
      }),
    enabled: Boolean(accessToken),
  });

  const previewTotals = React.useMemo(() => {
    let sub = 0;
    let vat = 0;
    for (const l of lines) {
      const qty = Number.parseFloat(l.quantity) || 0;
      const pricePoisha = parsePoisha(l.unit_price);
      const vatPct = Number.parseFloat(l.vat_rate_percent) || 0;
      const lineSub = Math.round(qty * pricePoisha);
      const lineVat = Math.round((lineSub * vatPct) / 100);
      sub += lineSub;
      vat += lineVat;
    }
    return { sub, vat, grand: sub + vat };
  }, [lines]);

  const createMutation = useMutation({
    mutationFn: () =>
      apiRequest<SalesInvoiceItem>("/sales/invoices", {
        method: "POST",
        accessToken,
        body: {
          customer_id: customerId,
          invoice_date: invoiceDate,
          due_date: dueDate,
          lines: lines.map((l) => ({
            description: l.description,
            quantity: l.quantity || "1",
            unit_price: poishaToStr(parsePoisha(l.unit_price)),
            vat_rate_percent: poishaToStr(parsePoisha(l.vat_rate_percent)),
          })),
        },
      }),
    onSuccess: () => {
      setFormError(null);
      setLines([
        {
          key: `il-${String(Date.now())}`,
          description: "",
          quantity: "1",
          unit_price: "",
          vat_rate_percent: "0.00",
        },
      ]);
      void queryClient.invalidateQueries({ queryKey: ["sales", "invoices"] });
    },
    onError: (err: unknown) => {
      setFormError(err instanceof ApiError ? err.message : "Failed to create invoice.");
    },
  });

  const postMutation = useMutation({
    mutationFn: (invoiceId: string) =>
      apiRequest<SalesInvoiceItem>(`/sales/invoices/${invoiceId}/post`, {
        method: "POST",
        accessToken,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["sales"] });
      void queryClient.invalidateQueries({ queryKey: ["accounting"] });
    },
  });

  const payMutation = useMutation({
    mutationFn: () => {
      if (!payingInvoice) throw new Error("No invoice selected");
      return apiRequest<CustomerPaymentItem>(`/sales/invoices/${payingInvoice.id}/payments`, {
        method: "POST",
        accessToken,
        body: {
          payment_date: today,
          amount: poishaToStr(parsePoisha(payAmount)),
          payment_method: payMethod,
          deposit_account_id: depositAccountId,
        },
      });
    },
    onSuccess: () => {
      setPayingInvoice(null);
      setPayError(null);
      setPayAmount("");
      void queryClient.invalidateQueries({ queryKey: ["sales"] });
      void queryClient.invalidateQueries({ queryKey: ["accounting"] });
    },
    onError: (err: unknown) => {
      setPayError(err instanceof ApiError ? err.message : "Failed to record payment.");
    },
  });

  const updateLine = (key: string, patch: Partial<DraftInvLine>): void => {
    setLines((prev) => prev.map((l) => (l.key === key ? { ...l, ...patch } : l)));
  };

  const handleSubmit = (e: React.FormEvent): void => {
    e.preventDefault();
    setFormError(null);
    if (!customerId) {
      setFormError("Please select a customer.");
      return;
    }
    if (lines.some((l) => !l.description.trim() || parsePoisha(l.unit_price) <= 0)) {
      setFormError("Every line must have a description and unit price.");
      return;
    }
    createMutation.mutate();
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{t("sales.invoicesTitle")}</h1>
        <p className="text-sm text-muted-foreground">{t("sales.invoicesSubtitle")}</p>
      </div>

      {canWrite ? (
        <Card>
          <CardHeader>
            <CardTitle>{t("sales.newInvoice")}</CardTitle>
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
                  <Label htmlFor="inv_cust">{t("sales.customer")}</Label>
                  <select
                    id="inv_cust"
                    className="flex h-10 w-full rounded-md border border-input bg-card px-3 text-sm"
                    value={customerId}
                    onChange={(e) => { setCustomerId(e.target.value); }}
                  >
                    <option value="">-- Select Customer --</option>
                    {(customersQuery.data?.items ?? []).map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.code} — {c.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="space-y-1">
                  <Label htmlFor="inv_date">{t("sales.invoiceDate")}</Label>
                  <Input
                    id="inv_date"
                    type="date"
                    value={invoiceDate}
                    onChange={(e) => { setInvoiceDate(e.target.value); }}
                  />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="inv_due">{t("sales.dueDate")}</Label>
                  <Input
                    id="inv_due"
                    type="date"
                    value={dueDate}
                    onChange={(e) => { setDueDate(e.target.value); }}
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
                          key: `il-${String(Date.now())}-${String(prev.length)}`,
                          description: "",
                          quantity: "1",
                          unit_price: "",
                          vat_rate_percent: "0.00",
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
                    <Input
                      className="sm:col-span-5"
                      placeholder={t("sales.description")}
                      value={line.description}
                      onChange={(e) => { updateLine(line.key, { description: e.target.value }); }}
                    />
                    <Input
                      className="sm:col-span-2"
                      inputMode="decimal"
                      placeholder={t("sales.qty")}
                      value={line.quantity}
                      onChange={(e) => { updateLine(line.key, { quantity: e.target.value }); }}
                    />
                    <Input
                      className="sm:col-span-2"
                      inputMode="decimal"
                      placeholder={t("sales.unitPrice")}
                      value={line.unit_price}
                      onChange={(e) => { updateLine(line.key, { unit_price: e.target.value }); }}
                    />
                    <Input
                      className="sm:col-span-2"
                      inputMode="decimal"
                      placeholder={t("sales.vatPercent")}
                      value={line.vat_rate_percent}
                      onChange={(e) => {
                        updateLine(line.key, { vat_rate_percent: e.target.value });
                      }}
                    />
                    <div className="flex items-center justify-end sm:col-span-1">
                      {lines.length > 1 ? (
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
                <div className="flex flex-wrap gap-5 text-sm font-medium tabular-nums">
                  <span>
                    {t("sales.subtotal")}: {formatBDT(poishaToStr(previewTotals.sub), { banglaDigits })}
                  </span>
                  <span>
                    {t("sales.vatTotal")}: {formatBDT(poishaToStr(previewTotals.vat), { banglaDigits })}
                  </span>
                  <span className="font-bold text-primary">
                    {t("sales.grandTotal")}: {formatBDT(poishaToStr(previewTotals.grand), { banglaDigits })}
                  </span>
                </div>
                <Button type="submit" disabled={createMutation.isPending}>
                  {t("sales.saveDraft")}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      ) : null}

      {payingInvoice && canPay ? (
        <Card className="border-primary">
          <CardHeader>
            <CardTitle>
              {t("sales.receivePayment")} — {payingInvoice.invoice_no}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {payError ? (
              <div role="alert" className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {payError}
              </div>
            ) : null}
            <div className="grid gap-4 sm:grid-cols-3">
              <div className="space-y-1">
                <Label htmlFor="pay_amt">Amount (৳)</Label>
                <Input
                  id="pay_amt"
                  inputMode="decimal"
                  value={payAmount}
                  onChange={(e) => { setPayAmount(e.target.value); }}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="pay_method">{t("sales.paymentMethod")}</Label>
                <select
                  id="pay_method"
                  className="flex h-10 w-full rounded-md border border-input bg-card px-3 text-sm"
                  value={payMethod}
                  onChange={(e) => { setPayMethod(e.target.value as PaymentMethod); }}
                >
                  <option value="cash">Cash</option>
                  <option value="bank">Bank Transfer</option>
                  <option value="mfs">MFS (bKash/Nagad)</option>
                  <option value="cheque">Cheque</option>
                </select>
              </div>
              <div className="space-y-1">
                <Label htmlFor="pay_acc">{t("sales.depositAccount")}</Label>
                <select
                  id="pay_acc"
                  className="flex h-10 w-full rounded-md border border-input bg-card px-3 text-sm"
                  value={depositAccountId}
                  onChange={(e) => { setDepositAccountId(e.target.value); }}
                >
                  <option value="">-- Select Cash / Bank --</option>
                  {depositAccounts.map((acc) => (
                    <option key={acc.id} value={acc.id}>
                      {acc.code} — {acc.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="flex gap-2">
              <Button disabled={payMutation.isPending} onClick={() => { payMutation.mutate(); }}>
                {t("sales.recordPayment")}
              </Button>
              <Button variant="outline" onClick={() => { setPayingInvoice(null); }}>
                {t("accounting.cancel")}
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>{t("sales.invoicesTitle")}</CardTitle>
        </CardHeader>
        <CardContent>
          {invoicesQuery.isLoading ? (
            <TableSkeleton rows={5} columns={6} />
          ) : invoicesQuery.isError ? (
            <ErrorState
              title={t("sales.invoicesErrorTitle")}
              message={invoicesQuery.error.message}
              retryLabel={t("dashboard.retry")}
              onRetry={() => void invoicesQuery.refetch()}
            />
          ) : !invoicesQuery.data || invoicesQuery.data.items.length === 0 ? (
            <EmptyState
              title={t("sales.invoicesEmptyTitle")}
              description={t("sales.invoicesEmptyDesc")}
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-border text-xs uppercase text-muted-foreground">
                  <tr>
                    <th className="pb-2 pr-4">Invoice</th>
                    <th className="pb-2 pr-4">{t("sales.invoiceDate")}</th>
                    <th className="pb-2 pr-4 text-right">{t("sales.grandTotal")}</th>
                    <th className="pb-2 pr-4 text-right">{t("sales.paid")}</th>
                    <th className="pb-2 pr-4">Status</th>
                    <th className="pb-2 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {invoicesQuery.data.items.map((inv) => {
                    const duePoisha = parsePoisha(inv.grand_total) - parsePoisha(inv.paid_amount);
                    return (
                      <tr key={inv.id}>
                        <td className="py-3 pr-4 font-mono text-xs font-medium">{inv.invoice_no}</td>
                        <td className="py-3 pr-4 tabular-nums">{inv.invoice_date}</td>
                        <td className="py-3 pr-4 text-right tabular-nums">
                          {formatBDT(inv.grand_total, { banglaDigits })}
                        </td>
                        <td className="py-3 pr-4 text-right tabular-nums">
                          {formatBDT(inv.paid_amount, { banglaDigits })}
                        </td>
                        <td className="py-3 pr-4">
                          <Badge variant={inv.status === "paid" || inv.status === "posted" ? "default" : "secondary"}>
                            {inv.status.replace("_", " ").toUpperCase()}
                          </Badge>
                        </td>
                        <td className="py-3 text-right">
                          {canPost && inv.status === "draft" ? (
                            <Button
                              size="sm"
                              disabled={postMutation.isPending}
                              onClick={() => { postMutation.mutate(inv.id); }}
                            >
                              {t("sales.postToGl")}
                            </Button>
                          ) : null}
                          {canPay && (inv.status === "posted" || inv.status === "partially_paid") ? (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => {
                                setPayingInvoice(inv);
                                setPayAmount(poishaToStr(duePoisha));
                                setPayError(null);
                              }}
                            >
                              {t("sales.receivePayment")}
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
