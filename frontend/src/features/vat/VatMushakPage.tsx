import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Info, FileText, Plus, Printer, X } from "lucide-react";
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
import { useAuthStore } from "@/features/auth/store";
import type {
  Mushak61Report,
  Mushak62Report,
  Mushak63Challan,
  Mushak91Summary,
  PaginatedVatRates,
  VatRateItem,
} from "@/features/vat/types";
import { apiRequest } from "@/lib/api";
import { formatBDT } from "@/lib/format";

type VatTab = "m91" | "m61" | "m62" | "rates";

function buildDateParams(dateFrom: string, dateTo: string): string {
  const params = new URLSearchParams();
  if (dateFrom) {
    params.set("date_from", dateFrom);
  }
  if (dateTo) {
    params.set("date_to", dateTo);
  }
  const qs = params.toString();
  return qs ? `?${qs}` : "";
}

export function VatMushakPage(): React.JSX.Element {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const accessToken = useAuthStore((s) => s.accessToken);
  const permissions = useAuthStore((s) => s.permissions);
  const banglaDigits = useAuthStore((s) => s.banglaDigits);

  const canWriteRates = permissions.includes("vat.rates.write");
  const canReadRates = permissions.includes("vat.rates.read");

  const [activeTab, setActiveTab] = React.useState<VatTab>("m91");
  const [dateFrom, setDateFrom] = React.useState("");
  const [dateTo, setDateTo] = React.useState("");
  const [selectedInvoiceId, setSelectedInvoiceId] = React.useState<string | null>(null);

  // Configurable VAT rate form state
  const [showRateForm, setShowRateForm] = React.useState(false);
  const [rateCode, setRateCode] = React.useState("");
  const [rateName, setRateName] = React.useState("");
  const [ratePercent, setRatePercent] = React.useState("15.00");
  const [isVdsApplicable, setIsVdsApplicable] = React.useState(false);
  const [statutoryNote, setStatutoryNote] = React.useState("");
  const [rateError, setRateError] = React.useState<string | null>(null);

  const dateQs = buildDateParams(dateFrom, dateTo);

  const m91Query = useQuery({
    queryKey: ["vat", "mushak-9-1", dateFrom, dateTo],
    queryFn: ({ signal }) =>
      apiRequest<Mushak91Summary>(`/vat/mushak/9-1${dateQs}`, { accessToken, signal }),
    enabled: Boolean(accessToken) && activeTab === "m91",
  });

  const m61Query = useQuery({
    queryKey: ["vat", "mushak-6-1", dateFrom, dateTo],
    queryFn: ({ signal }) =>
      apiRequest<Mushak61Report>(`/vat/mushak/6-1${dateQs}`, { accessToken, signal }),
    enabled: Boolean(accessToken) && activeTab === "m61",
  });

  const m62Query = useQuery({
    queryKey: ["vat", "mushak-6-2", dateFrom, dateTo],
    queryFn: ({ signal }) =>
      apiRequest<Mushak62Report>(`/vat/mushak/6-2${dateQs}`, { accessToken, signal }),
    enabled: Boolean(accessToken) && activeTab === "m62",
  });

  const m63Query = useQuery({
    queryKey: ["vat", "mushak-6-3", selectedInvoiceId],
    queryFn: ({ signal }) =>
      apiRequest<Mushak63Challan>(`/vat/mushak/6-3/${selectedInvoiceId ?? ""}`, {
        accessToken,
        signal,
      }),
    enabled: Boolean(accessToken) && Boolean(selectedInvoiceId),
  });

  const ratesQuery = useQuery({
    queryKey: ["vat", "rates"],
    queryFn: ({ signal }) =>
      apiRequest<PaginatedVatRates>("/vat/rates?page=1&page_size=100", { accessToken, signal }),
    enabled: Boolean(accessToken) && canReadRates && activeTab === "rates",
  });

  const createRateMutation = useMutation({
    mutationFn: () =>
      apiRequest<VatRateItem>("/vat/rates", {
        method: "POST",
        accessToken,
        body: {
          code: rateCode.trim().toUpperCase(),
          name: rateName.trim(),
          rate_percent: ratePercent.trim(),
          is_vds_applicable: isVdsApplicable,
          statutory_note: statutoryNote.trim(),
        },
      }),
    onSuccess: () => {
      setRateCode("");
      setRateName("");
      setRatePercent("15.00");
      setIsVdsApplicable(false);
      setStatutoryNote("");
      setRateError(null);
      setShowRateForm(false);
      void queryClient.invalidateQueries({ queryKey: ["vat", "rates"] });
    },
    onError: (err: Error) => {
      setRateError(err.message);
    },
  });

  const handleRateSubmit = (e: React.FormEvent): void => {
    e.preventDefault();
    setRateError(null);
    createRateMutation.mutate();
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4 print:hidden">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{t("vat.title")}</h1>
          <p className="text-sm text-muted-foreground">{t("vat.subtitle")}</p>
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <div className="space-y-1">
            <Label htmlFor="vat-date-from">{t("vat.dateFrom")}</Label>
            <Input
              id="vat-date-from"
              type="date"
              value={dateFrom}
              onChange={(e) => {
                setDateFrom(e.target.value);
              }}
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="vat-date-to">{t("vat.dateTo")}</Label>
            <Input
              id="vat-date-to"
              type="date"
              value={dateTo}
              onChange={(e) => {
                setDateTo(e.target.value);
              }}
            />
          </div>
          {dateFrom || dateTo ? (
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setDateFrom("");
                setDateTo("");
              }}
            >
              {t("vat.clearDates")}
            </Button>
          ) : null}
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex flex-wrap gap-2 border-b border-border pb-3 print:hidden" role="tablist">
        {(
          [
            ["m91", t("vat.tabMushak91")],
            ["m61", t("vat.tabMushak61")],
            ["m62", t("vat.tabMushak62")],
            ...(canReadRates ? ([["rates", t("vat.tabRates")]] as [VatTab, string][]) : []),
          ] as [VatTab, string][]
        ).map(([tabKey, label]) => (
          <Button
            key={tabKey}
            role="tab"
            aria-selected={activeTab === tabKey}
            variant={activeTab === tabKey ? "default" : "outline"}
            size="sm"
            onClick={() => {
              setActiveTab(tabKey);
            }}
          >
            {label}
          </Button>
        ))}
      </div>

      {/* MUSHAK 9.1 SUMMARY */}
      {activeTab === "m91" ? (
        <div className="space-y-4">
          {m91Query.isLoading ? (
            <TableSkeleton rows={4} columns={4} />
          ) : m91Query.isError ? (
            <ErrorState
              title={t("vat.loadError")}
              message={m91Query.error.message}
              retryLabel={t("dashboard.retry")}
              onRetry={() => void m91Query.refetch()}
            />
          ) : m91Query.data ? (
            <>
              <div
                role="note"
                className="flex items-start gap-3 rounded-lg border border-primary/20 bg-primary/5 p-4 text-sm text-foreground"
              >
                <Info className="mt-0.5 h-5 w-5 shrink-0 text-primary" aria-hidden="true" />
                <div>
                  <p className="font-semibold">{t("vat.advisoryTitle")}</p>
                  <p className="mt-0.5 text-muted-foreground">{m91Query.data.advisory_note}</p>
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">
                      {t("vat.outputVat")}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-2xl font-bold tabular-nums">
                      {formatBDT(m91Query.data.total_output_vat, { banglaDigits })}
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {t("vat.taxableSales")}:{" "}
                      {formatBDT(m91Query.data.total_sales_taxable, { banglaDigits })}
                    </p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">
                      {t("vat.inputVat")}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-2xl font-bold tabular-nums">
                      {formatBDT(m91Query.data.total_input_vat, { banglaDigits })}
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {t("vat.taxablePurchases")}:{" "}
                      {formatBDT(m91Query.data.total_purchase_taxable, { banglaDigits })}
                    </p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">
                      {t("vat.netVatPayable")}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-2xl font-bold tabular-nums text-primary">
                      {formatBDT(m91Query.data.net_vat_payable, { banglaDigits })}
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {t("vat.carryForwardCredit")}:{" "}
                      {formatBDT(m91Query.data.carry_forward_credit, { banglaDigits })}
                    </p>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">
                      {t("vat.withholdingSummary")}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-lg font-bold tabular-nums">
                      {t("vat.vds")}:{" "}
                      {formatBDT(m91Query.data.total_vds_payable, { banglaDigits })}
                    </p>
                    <p className="mt-1 text-sm font-medium tabular-nums text-muted-foreground">
                      {t("vat.tds")}:{" "}
                      {formatBDT(m91Query.data.total_tds_payable, { banglaDigits })}
                    </p>
                  </CardContent>
                </Card>
              </div>
            </>
          ) : null}
        </div>
      ) : null}

      {/* MUSHAK 6.1 PURCHASE REGISTER */}
      {activeTab === "m61" ? (
        <Card>
          <CardHeader>
            <CardTitle>{t("vat.mushak61Title")}</CardTitle>
          </CardHeader>
          <CardContent>
            {m61Query.isLoading ? (
              <TableSkeleton rows={5} columns={7} />
            ) : m61Query.isError ? (
              <ErrorState
                title={t("vat.loadError")}
                message={m61Query.error.message}
                retryLabel={t("dashboard.retry")}
                onRetry={() => void m61Query.refetch()}
              />
            ) : !m61Query.data || m61Query.data.items.length === 0 ? (
              <EmptyState
                title={t("vat.emptyMushak61Title")}
                description={t("vat.emptyMushak61Desc")}
              />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="border-b border-border text-xs uppercase text-muted-foreground">
                    <tr>
                      <th className="pb-2 pr-4">{t("vat.billNo")}</th>
                      <th className="pb-2 pr-4">{t("vat.date")}</th>
                      <th className="pb-2 pr-4">{t("vat.supplier")}</th>
                      <th className="pb-2 pr-4 text-right">{t("vat.taxableValue")}</th>
                      <th className="pb-2 pr-4 text-right">{t("vat.inputVat")}</th>
                      <th className="pb-2 pr-4 text-right">{t("vat.vds")}</th>
                      <th className="pb-2 pr-4 text-right">{t("vat.tds")}</th>
                      <th className="pb-2 text-right">{t("vat.grossTotal")}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {m61Query.data.items.map((item) => (
                      <tr key={item.bill_id}>
                        <td className="py-2.5 pr-4 font-mono text-xs">{item.bill_no}</td>
                        <td className="py-2.5 pr-4">{item.bill_date}</td>
                        <td className="py-2.5 pr-4">
                          <div className="font-medium">{item.supplier_name}</div>
                          {item.supplier_bin ? (
                            <div className="text-xs text-muted-foreground">
                              BIN: {item.supplier_bin}
                            </div>
                          ) : null}
                        </td>
                        <td className="py-2.5 pr-4 text-right tabular-nums">
                          {formatBDT(item.taxable_value, { banglaDigits })}
                        </td>
                        <td className="py-2.5 pr-4 text-right tabular-nums">
                          {formatBDT(item.input_vat, { banglaDigits })}
                        </td>
                        <td className="py-2.5 pr-4 text-right tabular-nums">
                          {formatBDT(item.vds_amount, { banglaDigits })}
                        </td>
                        <td className="py-2.5 pr-4 text-right tabular-nums">
                          {formatBDT(item.tds_amount, { banglaDigits })}
                        </td>
                        <td className="py-2.5 text-right font-medium tabular-nums">
                          {formatBDT(item.gross_total, { banglaDigits })}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot className="border-t-2 border-border font-bold">
                    <tr>
                      <td colSpan={3} className="pt-3 pr-4">
                        {t("accounting.grandTotal")}
                      </td>
                      <td className="pt-3 pr-4 text-right tabular-nums">
                        {formatBDT(m61Query.data.total_taxable_value, { banglaDigits })}
                      </td>
                      <td className="pt-3 pr-4 text-right tabular-nums">
                        {formatBDT(m61Query.data.total_input_vat, { banglaDigits })}
                      </td>
                      <td className="pt-3 pr-4 text-right tabular-nums">
                        {formatBDT(m61Query.data.total_vds, { banglaDigits })}
                      </td>
                      <td className="pt-3 pr-4 text-right tabular-nums">
                        {formatBDT(m61Query.data.total_tds, { banglaDigits })}
                      </td>
                      <td />
                    </tr>
                  </tfoot>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      ) : null}

      {/* MUSHAK 6.2 SALES REGISTER + MUSHAK 6.3 CHALLAN VIEWER */}
      {activeTab === "m62" ? (
        <div className="space-y-6">
          {selectedInvoiceId ? (
            <Card className="border-primary/40">
              <CardHeader className="flex flex-row items-center justify-between gap-2">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <FileText className="h-5 w-5 text-primary" aria-hidden="true" />
                    {t("vat.mushak63Title")}
                  </CardTitle>
                </div>
                <div className="flex items-center gap-2 print:hidden">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      window.print();
                    }}
                  >
                    <Printer className="h-4 w-4" aria-hidden="true" />
                    {t("vat.printChallan")}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    aria-label="Close Mushak 6.3"
                    onClick={() => {
                      setSelectedInvoiceId(null);
                    }}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {m63Query.isLoading ? (
                  <TableSkeleton rows={4} columns={5} />
                ) : m63Query.isError ? (
                  <ErrorState
                    title={t("vat.loadError")}
                    message={m63Query.error.message}
                    retryLabel={t("dashboard.retry")}
                    onRetry={() => void m63Query.refetch()}
                  />
                ) : m63Query.data ? (
                  <div className="space-y-4">
                    <div className="grid gap-4 rounded-md bg-secondary/40 p-4 text-sm sm:grid-cols-2">
                      <div>
                        <p className="text-xs uppercase text-muted-foreground">{t("vat.seller")}</p>
                        <p className="font-semibold">{m63Query.data.seller_name}</p>
                        <p className="mt-2 text-xs text-muted-foreground">
                          {t("vat.invoiceNo")}:{" "}
                          <span className="font-mono text-foreground">
                            {m63Query.data.invoice_no}
                          </span>
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {t("vat.date")}:{" "}
                          <span className="text-foreground">{m63Query.data.invoice_date}</span>
                        </p>
                      </div>
                      <div>
                        <p className="text-xs uppercase text-muted-foreground">
                          {t("vat.customer")}
                        </p>
                        <p className="font-semibold">{m63Query.data.customer_name}</p>
                        {m63Query.data.customer_bin ? (
                          <p className="text-xs text-muted-foreground">
                            BIN: {m63Query.data.customer_bin}
                          </p>
                        ) : null}
                        {m63Query.data.customer_address ? (
                          <p className="text-xs text-muted-foreground">
                            {m63Query.data.customer_address}
                          </p>
                        ) : null}
                      </div>
                    </div>

                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-sm">
                        <thead className="border-b border-border text-xs uppercase text-muted-foreground">
                          <tr>
                            <th className="pb-2 pr-3">#</th>
                            <th className="pb-2 pr-3">{t("sales.description")}</th>
                            <th className="pb-2 pr-3 text-right">{t("sales.qty")}</th>
                            <th className="pb-2 pr-3 text-right">{t("sales.unitPrice")}</th>
                            <th className="pb-2 pr-3 text-right">{t("sales.vatPercent")}</th>
                            <th className="pb-2 pr-3 text-right">{t("sales.subtotal")}</th>
                            <th className="pb-2 pr-3 text-right">{t("sales.vatTotal")}</th>
                            <th className="pb-2 text-right">{t("sales.grandTotal")}</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-border">
                          {m63Query.data.lines.map((line) => (
                            <tr key={line.line_no}>
                              <td className="py-2 pr-3">{line.line_no}</td>
                              <td className="py-2 pr-3 font-medium">{line.description}</td>
                              <td className="py-2 pr-3 text-right tabular-nums">{line.quantity}</td>
                              <td className="py-2 pr-3 text-right tabular-nums">
                                {formatBDT(line.unit_price, { banglaDigits })}
                              </td>
                              <td className="py-2 pr-3 text-right tabular-nums">
                                {line.vat_rate_percent}%
                              </td>
                              <td className="py-2 pr-3 text-right tabular-nums">
                                {formatBDT(line.line_subtotal, { banglaDigits })}
                              </td>
                              <td className="py-2 pr-3 text-right tabular-nums">
                                {formatBDT(line.line_vat, { banglaDigits })}
                              </td>
                              <td className="py-2 text-right font-medium tabular-nums">
                                {formatBDT(line.line_total, { banglaDigits })}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                        <tfoot className="border-t-2 border-border font-bold">
                          <tr>
                            <td colSpan={5} className="pt-3 pr-3 text-right">
                              {t("accounting.grandTotal")}
                            </td>
                            <td className="pt-3 pr-3 text-right tabular-nums">
                              {formatBDT(m63Query.data.subtotal, { banglaDigits })}
                            </td>
                            <td className="pt-3 pr-3 text-right tabular-nums">
                              {formatBDT(m63Query.data.vat_total, { banglaDigits })}
                            </td>
                            <td className="pt-3 text-right tabular-nums">
                              {formatBDT(m63Query.data.grand_total, { banglaDigits })}
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
              <CardTitle>{t("vat.mushak62Title")}</CardTitle>
            </CardHeader>
            <CardContent>
              {m62Query.isLoading ? (
                <TableSkeleton rows={5} columns={6} />
              ) : m62Query.isError ? (
                <ErrorState
                  title={t("vat.loadError")}
                  message={m62Query.error.message}
                  retryLabel={t("dashboard.retry")}
                  onRetry={() => void m62Query.refetch()}
                />
              ) : !m62Query.data || m62Query.data.items.length === 0 ? (
                <EmptyState
                  title={t("vat.emptyMushak62Title")}
                  description={t("vat.emptyMushak62Desc")}
                />
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="border-b border-border text-xs uppercase text-muted-foreground">
                      <tr>
                        <th className="pb-2 pr-4">{t("vat.invoiceNo")}</th>
                        <th className="pb-2 pr-4">{t("vat.date")}</th>
                        <th className="pb-2 pr-4">{t("vat.customer")}</th>
                        <th className="pb-2 pr-4 text-right">{t("vat.taxableValue")}</th>
                        <th className="pb-2 pr-4 text-right">{t("vat.outputVat")}</th>
                        <th className="pb-2 pr-4 text-right">{t("sales.grandTotal")}</th>
                        <th className="pb-2 text-right">{t("vat.challanAction")}</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {m62Query.data.items.map((item) => (
                        <tr key={item.invoice_id}>
                          <td className="py-2.5 pr-4 font-mono text-xs">{item.invoice_no}</td>
                          <td className="py-2.5 pr-4">{item.invoice_date}</td>
                          <td className="py-2.5 pr-4">
                            <div className="font-medium">{item.customer_name}</div>
                            {item.customer_bin ? (
                              <div className="text-xs text-muted-foreground">
                                BIN: {item.customer_bin}
                              </div>
                            ) : null}
                          </td>
                          <td className="py-2.5 pr-4 text-right tabular-nums">
                            {formatBDT(item.taxable_value, { banglaDigits })}
                          </td>
                          <td className="py-2.5 pr-4 text-right tabular-nums">
                            {formatBDT(item.output_vat, { banglaDigits })}
                          </td>
                          <td className="py-2.5 pr-4 text-right font-medium tabular-nums">
                            {formatBDT(item.grand_total, { banglaDigits })}
                          </td>
                          <td className="py-2.5 text-right">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => {
                                setSelectedInvoiceId(item.invoice_id);
                              }}
                            >
                              {t("vat.viewMushak63")}
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot className="border-t-2 border-border font-bold">
                      <tr>
                        <td colSpan={3} className="pt-3 pr-4">
                          {t("accounting.grandTotal")}
                        </td>
                        <td className="pt-3 pr-4 text-right tabular-nums">
                          {formatBDT(m62Query.data.total_taxable_value, { banglaDigits })}
                        </td>
                        <td className="pt-3 pr-4 text-right tabular-nums">
                          {formatBDT(m62Query.data.total_output_vat, { banglaDigits })}
                        </td>
                        <td className="pt-3 pr-4 text-right tabular-nums">
                          {formatBDT(m62Query.data.total_grand_total, { banglaDigits })}
                        </td>
                        <td />
                      </tr>
                    </tfoot>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      ) : null}

      {/* CONFIGURABLE VAT RATES */}
      {activeTab === "rates" && canReadRates ? (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">{t("vat.ratesSubtitle")}</p>
            {canWriteRates ? (
              <Button
                size="sm"
                onClick={() => {
                  setShowRateForm((v) => !v);
                }}
              >
                <Plus className="h-4 w-4" aria-hidden="true" />
                {t("vat.newRate")}
              </Button>
            ) : null}
          </div>

          {showRateForm && canWriteRates ? (
            <Card>
              <CardHeader>
                <CardTitle>{t("vat.newRate")}</CardTitle>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleRateSubmit} className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  <div className="space-y-1">
                    <Label htmlFor="vat-rate-code">{t("vat.rateCode")}</Label>
                    <Input
                      id="vat-rate-code"
                      required
                      placeholder="VAT-15"
                      value={rateCode}
                      onChange={(e) => {
                        setRateCode(e.target.value);
                      }}
                    />
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor="vat-rate-name">{t("vat.rateName")}</Label>
                    <Input
                      id="vat-rate-name"
                      required
                      placeholder="Standard VAT 15%"
                      value={rateName}
                      onChange={(e) => {
                        setRateName(e.target.value);
                      }}
                    />
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor="vat-rate-percent">{t("vat.ratePercent")}</Label>
                    <Input
                      id="vat-rate-percent"
                      type="number"
                      step="0.01"
                      min="0"
                      max="100"
                      required
                      value={ratePercent}
                      onChange={(e) => {
                        setRatePercent(e.target.value);
                      }}
                    />
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor="vat-rate-note">{t("vat.statutoryNote")}</Label>
                    <Input
                      id="vat-rate-note"
                      placeholder="SRO / NBR reference..."
                      value={statutoryNote}
                      onChange={(e) => {
                        setStatutoryNote(e.target.value);
                      }}
                    />
                  </div>
                  <div className="flex items-center gap-2 sm:col-span-2">
                    <input
                      id="vat-rate-vds"
                      type="checkbox"
                      checked={isVdsApplicable}
                      onChange={(e) => {
                        setIsVdsApplicable(e.target.checked);
                      }}
                    />
                    <Label htmlFor="vat-rate-vds">{t("vat.vdsApplicable")}</Label>
                  </div>
                  <div className="flex items-center justify-end gap-2 sm:col-span-2">
                    {rateError ? <p className="text-sm text-destructive">{rateError}</p> : null}
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => {
                        setShowRateForm(false);
                      }}
                    >
                      {t("accounting.cancel")}
                    </Button>
                    <Button type="submit" disabled={createRateMutation.isPending}>
                      {t("vat.saveRate")}
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          ) : null}

          <Card>
            <CardHeader>
              <CardTitle>{t("vat.tabRates")}</CardTitle>
            </CardHeader>
            <CardContent>
              {ratesQuery.isLoading ? (
                <TableSkeleton rows={4} columns={5} />
              ) : ratesQuery.isError ? (
                <ErrorState
                  title={t("vat.loadError")}
                  message={ratesQuery.error.message}
                  retryLabel={t("dashboard.retry")}
                  onRetry={() => void ratesQuery.refetch()}
                />
              ) : !ratesQuery.data || ratesQuery.data.items.length === 0 ? (
                <EmptyState
                  title={t("vat.emptyRatesTitle")}
                  description={t("vat.emptyRatesDesc")}
                />
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="border-b border-border text-xs uppercase text-muted-foreground">
                      <tr>
                        <th className="pb-2 pr-4">{t("vat.rateCode")}</th>
                        <th className="pb-2 pr-4">{t("vat.rateName")}</th>
                        <th className="pb-2 pr-4 text-right">{t("vat.ratePercent")}</th>
                        <th className="pb-2 pr-4">{t("vat.vds")}</th>
                        <th className="pb-2">{t("vat.statutoryNote")}</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {ratesQuery.data.items.map((rate) => (
                        <tr key={rate.id}>
                          <td className="py-2.5 pr-4 font-mono text-xs">{rate.code}</td>
                          <td className="py-2.5 pr-4 font-medium">{rate.name}</td>
                          <td className="py-2.5 pr-4 text-right tabular-nums">
                            {rate.rate_percent}%
                          </td>
                          <td className="py-2.5 pr-4">
                            <Badge variant={rate.is_vds_applicable ? "default" : "secondary"}>
                              {rate.is_vds_applicable ? t("vat.vdsYes") : t("vat.vdsNo")}
                            </Badge>
                          </td>
                          <td className="py-2.5 text-muted-foreground">
                            {rate.statutory_note || "—"}
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
      ) : null}
    </div>
  );
}
