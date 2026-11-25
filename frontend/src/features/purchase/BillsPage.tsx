import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Banknote, CheckCircle2, Plus, Trash2 } from "lucide-react";
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
  PaymentMethod,
  PurchaseBillItem,
  SupplierItem,
  SupplierPaymentItem,
} from "@/features/purchase/types";
import { ApiError, apiRequest, type PaginatedResponse } from "@/lib/api";
import { formatBDT } from "@/lib/format";

interface DraftBillLine {
  key: string;
  description: string;
  quantity: string;
  unit_cost: string;
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

export function BillsPage(): React.JSX.Element {
  const { t } = useTranslation();
  const accessToken = useAuthStore((s) => s.accessToken);
  const permissions = useAuthStore((s) => s.permissions);
  const banglaDigits = useAuthStore((s) => s.banglaDigits);
  const canWrite = permissions.includes("purchase.bills.write");
  const canPost = permissions.includes("purchase.bills.post");
  const canPay = permissions.includes("purchase.payments.write");
  const queryClient = useQueryClient();

  const today = new Date().toISOString().slice(0, 10);
  const [supplierId, setSupplierId] = React.useState("");
  const [expenseAccountId, setExpenseAccountId] = React.useState("");
  const [billDate, setBillDate] = React.useState(today);
  const [dueDate, setDueDate] = React.useState(today);
  const [tdsPct, setTdsPct] = React.useState("0.00");
  const [vdsPct, setVdsPct] = React.useState("0.00");
  const [lines, setLines] = React.useState<DraftBillLine[]>([
    { key: "bl-1", description: "", quantity: "1", unit_cost: "", vat_rate_percent: "0.00" },
  ]);
  const [formError, setFormError] = React.useState<string | null>(null);

  const [payingBill, setPayingBill] = React.useState<PurchaseBillItem | null>(null);
  const [payAmount, setPayAmount] = React.useState("");
  const [payMethod, setPayMethod] = React.useState<PaymentMethod>("bank");
  const [payAccountId, setPayAccountId] = React.useState("");
  const [payError, setPayError] = React.useState<string | null>(null);

  const suppliersQuery = useQuery({
    queryKey: ["purchase", "suppliers", "dropdown"],
    queryFn: ({ signal }) =>
      apiRequest<PaginatedResponse<SupplierItem>>("/purchase/suppliers?page=1&page_size=100", {
        accessToken,
        signal,
      }),
    enabled: Boolean(accessToken),
  });

  const accountsQuery = useQuery({
    queryKey: ["accounting", "accounts", "all-for-purchase"],
    queryFn: ({ signal }) =>
      apiRequest<PaginatedResponse<AccountItem>>(
        "/accounting/accounts?page=1&page_size=100&sort_by=code&sort_dir=asc",
        { accessToken, signal },
      ),
    enabled: Boolean(accessToken),
  });

  const allPostable = React.useMemo(
    () => (accountsQuery.data?.items ?? []).filter((a) => !a.is_group && a.is_active),
    [accountsQuery.data],
  );
  const expenseOrAssetAccounts = React.useMemo(
    () => allPostable.filter((a) => a.account_type === "expense" || a.account_type === "asset"),
    [allPostable],
  );
  const assetAccounts = React.useMemo(
    () => allPostable.filter((a) => a.account_type === "asset"),
    [allPostable],
  );

  const billsQuery = useQuery({
    queryKey: ["purchase", "bills"],
    queryFn: ({ signal }) =>
      apiRequest<PaginatedResponse<PurchaseBillItem>>("/purchase/bills?page=1&page_size=25", {
        accessToken,
        signal,
      }),
    enabled: Boolean(accessToken),
  });

  const preview = React.useMemo(() => {
    let sub = 0;
    let vat = 0;
    for (const l of lines) {
      const qty = Number.parseFloat(l.quantity) || 0;
      const cost = parsePoisha(l.unit_cost);
      const vatP = Number.parseFloat(l.vat_rate_percent) || 0;
      const lSub = Math.round(qty * cost);
      sub += lSub;
      vat += Math.round((lSub * vatP) / 100);
    }
    const gross = sub + vat;
    const tds = Math.round((sub * (Number.parseFloat(tdsPct) || 0)) / 100);
    const vds = Math.round((sub * (Number.parseFloat(vdsPct) || 0)) / 100);
    return { sub, vat, gross, wh: tds + vds, net: gross - tds - vds };
  }, [lines, tdsPct, vdsPct]);

  const createMutation = useMutation({
    mutationFn: () =>
      apiRequest<PurchaseBillItem>("/purchase/bills", {
        method: "POST",
        accessToken,
        body: {
          supplier_id: supplierId,
          expense_account_id: expenseAccountId,
          bill_date: billDate,
          due_date: dueDate,
          tds_rate_percent: poishaToStr(parsePoisha(tdsPct)),
          vds_rate_percent: poishaToStr(parsePoisha(vdsPct)),
          lines: lines.map((l) => ({
            description: l.description,
            quantity: l.quantity || "1",
            unit_cost: poishaToStr(parsePoisha(l.unit_cost)),
            vat_rate_percent: poishaToStr(parsePoisha(l.vat_rate_percent)),
          })),
        },
      }),
    onSuccess: () => {
      setFormError(null);
      setLines([
        {
          key: `bl-${String(Date.now())}`,
          description: "",
          quantity: "1",
          unit_cost: "",
          vat_rate_percent: "0.00",
        },
      ]);
      void queryClient.invalidateQueries({ queryKey: ["purchase", "bills"] });
    },
    onError: (err: unknown) => {
      setFormError(err instanceof ApiError ? err.message : "Failed to save purchase bill.");
    },
  });

  const postMutation = useMutation({
    mutationFn: (billId: string) =>
      apiRequest<PurchaseBillItem>(`/purchase/bills/${billId}/post`, {
        method: "POST",
        accessToken,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["purchase"] });
      void queryClient.invalidateQueries({ queryKey: ["accounting"] });
    },
  });

  const payMutation = useMutation({
    mutationFn: () => {
      if (!payingBill) throw new Error("No bill selected");
      return apiRequest<SupplierPaymentItem>(`/purchase/bills/${payingBill.id}/payments`, {
        method: "POST",
        accessToken,
        body: {
          payment_date: today,
          amount: poishaToStr(parsePoisha(payAmount)),
          payment_method: payMethod,
          payment_account_id: payAccountId,
        },
      });
    },
    onSuccess: () => {
      setPayingBill(null);
      setPayError(null);
      setPayAmount("");
      void queryClient.invalidateQueries({ queryKey: ["purchase"] });
      void queryClient.invalidateQueries({ queryKey: ["accounting"] });
    },
    onError: (err: unknown) => {
      setPayError(err instanceof ApiError ? err.message : "Failed to record supplier payment.");
    },
  });

  const updateLine = (key: string, patch: Partial<DraftBillLine>): void => {
    setLines((prev) => prev.map((l) => (l.key === key ? { ...l, ...patch } : l)));
  };

  const handleSubmit = (e: React.FormEvent): void => {
    e.preventDefault();
    setFormError(null);
    if (!supplierId || !expenseAccountId) {
      setFormError("Please select both a supplier and an expense/inventory account.");
      return;
    }
    if (lines.some((l) => !l.description.trim() || parsePoisha(l.unit_cost) <= 0)) {
      setFormError("Every line must have a description and unit cost.");
      return;
    }
    createMutation.mutate();
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{t("purchase.billsTitle")}</h1>
        <p className="text-sm text-muted-foreground">{t("purchase.billsSubtitle")}</p>
      </div>

      {canWrite ? (
        <Card>
          <CardHeader>
            <CardTitle>{t("purchase.newBill")}</CardTitle>
          </CardHeader>
          <CardContent>
            {formError ? (
              <div role="alert" className="mb-4 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {formError}
              </div>
            ) : null}
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                <div className="space-y-1">
                  <Label htmlFor="bill_sup">{t("purchase.supplier")}</Label>
                  <select
                    id="bill_sup"
                    className="flex h-10 w-full rounded-md border border-input bg-card px-3 text-sm"
                    value={supplierId}
                    onChange={(e) => { setSupplierId(e.target.value); }}
                  >
                    <option value="">-- Select Supplier --</option>
                    {(suppliersQuery.data?.items ?? []).map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.code} — {s.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="space-y-1">
                  <Label htmlFor="bill_exp">{t("purchase.expenseAccount")}</Label>
                  <select
                    id="bill_exp"
                    className="flex h-10 w-full rounded-md border border-input bg-card px-3 text-sm"
                    value={expenseAccountId}
                    onChange={(e) => { setExpenseAccountId(e.target.value); }}
                  >
                    <option value="">-- Select Expense / Stock --</option>
                    {expenseOrAssetAccounts.map((a) => (
                      <option key={a.id} value={a.id}>
                        {a.code} — {a.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div className="space-y-1">
                    <Label htmlFor="bill_date">{t("purchase.billDate")}</Label>
                    <Input
                      id="bill_date"
                      type="date"
                      value={billDate}
                      onChange={(e) => { setBillDate(e.target.value); }}
                    />
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor="bill_due">{t("sales.dueDate")}</Label>
                    <Input
                      id="bill_due"
                      type="date"
                      value={dueDate}
                      onChange={(e) => { setDueDate(e.target.value); }}
                    />
                  </div>
                </div>
                <div className="space-y-1">
                  <Label htmlFor="bill_tds">{t("purchase.tdsPercent")}</Label>
                  <Input
                    id="bill_tds"
                    inputMode="decimal"
                    value={tdsPct}
                    onChange={(e) => { setTdsPct(e.target.value); }}
                  />
                </div>
                <div className="space-y-1">
                  <Label htmlFor="bill_vds">{t("purchase.vdsPercent")}</Label>
                  <Input
                    id="bill_vds"
                    inputMode="decimal"
                    value={vdsPct}
                    onChange={(e) => { setVdsPct(e.target.value); }}
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
                          key: `bl-${String(Date.now())}-${String(prev.length)}`,
                          description: "",
                          quantity: "1",
                          unit_cost: "",
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
                      placeholder={t("purchase.unitCost")}
                      value={line.unit_cost}
                      onChange={(e) => { updateLine(line.key, { unit_cost: e.target.value }); }}
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
                    {t("purchase.grossTotal")}: {formatBDT(poishaToStr(preview.gross), { banglaDigits })}
                  </span>
                  <span>
                    {t("purchase.tdsVds")}: {formatBDT(poishaToStr(preview.wh), { banglaDigits })}
                  </span>
                  <span className="font-bold text-primary">
                    {t("purchase.netPayable")}: {formatBDT(poishaToStr(preview.net), { banglaDigits })}
                  </span>
                </div>
                <Button type="submit" disabled={createMutation.isPending}>
                  {t("purchase.saveDraft")}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      ) : null}

      {payingBill && canPay ? (
        <Card className="border-primary">
          <CardHeader>
            <CardTitle>
              {t("purchase.paySupplier")} — {payingBill.bill_no}
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
                <Label htmlFor="spay_amt">Amount (৳)</Label>
                <Input
                  id="spay_amt"
                  inputMode="decimal"
                  value={payAmount}
                  onChange={(e) => { setPayAmount(e.target.value); }}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="spay_method">{t("sales.paymentMethod")}</Label>
                <select
                  id="spay_method"
                  className="flex h-10 w-full rounded-md border border-input bg-card px-3 text-sm"
                  value={payMethod}
                  onChange={(e) => { setPayMethod(e.target.value as PaymentMethod); }}
                >
                  <option value="bank">Bank Transfer</option>
                  <option value="cash">Cash</option>
                  <option value="mfs">MFS (bKash/Nagad)</option>
                  <option value="cheque">Cheque</option>
                </select>
              </div>
              <div className="space-y-1">
                <Label htmlFor="spay_acc">{t("purchase.paymentAccount")}</Label>
                <select
                  id="spay_acc"
                  className="flex h-10 w-full rounded-md border border-input bg-card px-3 text-sm"
                  value={payAccountId}
                  onChange={(e) => { setPayAccountId(e.target.value); }}
                >
                  <option value="">-- Select Cash / Bank --</option>
                  {assetAccounts.map((acc) => (
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
              <Button variant="outline" onClick={() => { setPayingBill(null); }}>
                {t("accounting.cancel")}
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>{t("purchase.billsTitle")}</CardTitle>
        </CardHeader>
        <CardContent>
          {billsQuery.isLoading ? (
            <TableSkeleton rows={5} columns={6} />
          ) : billsQuery.isError ? (
            <ErrorState
              title={t("purchase.billsErrorTitle")}
              message={billsQuery.error.message}
              retryLabel={t("dashboard.retry")}
              onRetry={() => void billsQuery.refetch()}
            />
          ) : !billsQuery.data || billsQuery.data.items.length === 0 ? (
            <EmptyState
              title={t("purchase.billsEmptyTitle")}
              description={t("purchase.billsEmptyDesc")}
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-border text-xs uppercase text-muted-foreground">
                  <tr>
                    <th className="pb-2 pr-4">Bill</th>
                    <th className="pb-2 pr-4">{t("purchase.billDate")}</th>
                    <th className="pb-2 pr-4 text-right">{t("purchase.netPayable")}</th>
                    <th className="pb-2 pr-4 text-right">{t("sales.paid")}</th>
                    <th className="pb-2 pr-4">Status</th>
                    <th className="pb-2 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {billsQuery.data.items.map((bill) => {
                    const duePoisha = parsePoisha(bill.net_payable) - parsePoisha(bill.paid_amount);
                    return (
                      <tr key={bill.id}>
                        <td className="py-3 pr-4 font-mono text-xs font-medium">{bill.bill_no}</td>
                        <td className="py-3 pr-4 tabular-nums">{bill.bill_date}</td>
                        <td className="py-3 pr-4 text-right tabular-nums">
                          {formatBDT(bill.net_payable, { banglaDigits })}
                        </td>
                        <td className="py-3 pr-4 text-right tabular-nums">
                          {formatBDT(bill.paid_amount, { banglaDigits })}
                        </td>
                        <td className="py-3 pr-4">
                          <Badge variant={bill.status === "paid" || bill.status === "posted" ? "default" : "secondary"}>
                            {bill.status.replace("_", " ").toUpperCase()}
                          </Badge>
                        </td>
                        <td className="py-3 text-right">
                          {canPost && bill.status === "draft" ? (
                            <Button
                              size="sm"
                              disabled={postMutation.isPending}
                              onClick={() => { postMutation.mutate(bill.id); }}
                            >
                              <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
                              {t("sales.postToGl")}
                            </Button>
                          ) : null}
                          {canPay && (bill.status === "posted" || bill.status === "partially_paid") ? (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => {
                                setPayingBill(bill);
                                setPayAmount(poishaToStr(duePoisha));
                                setPayError(null);
                              }}
                            >
                              <Banknote className="h-4 w-4" aria-hidden="true" />
                              {t("purchase.paySupplier")}
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
