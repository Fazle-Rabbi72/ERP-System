import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle } from "lucide-react";
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
  MovementType,
  ProductItem,
  StockSummaryResponse,
  WarehouseItem,
} from "@/features/inventory/types";
import { ApiError, apiRequest, type PaginatedResponse } from "@/lib/api";
import { formatBDT, toBanglaDigits } from "@/lib/format";

export function StockPage(): React.JSX.Element {
  const { t } = useTranslation();
  const accessToken = useAuthStore((s) => s.accessToken);
  const permissions = useAuthStore((s) => s.permissions);
  const banglaDigits = useAuthStore((s) => s.banglaDigits);
  const canMove = permissions.includes("inventory.stock.move");
  const queryClient = useQueryClient();

  const today = new Date().toISOString().slice(0, 10);
  const [movementType, setMovementType] = React.useState<MovementType>("in");
  const [warehouseId, setWarehouseId] = React.useState("");
  const [productId, setProductId] = React.useState("");
  const [quantity, setQuantity] = React.useState("1");
  const [reference, setReference] = React.useState("");
  const [formError, setFormError] = React.useState<string | null>(null);

  const whQuery = useQuery({
    queryKey: ["inventory", "warehouses", "dd"],
    queryFn: ({ signal }) =>
      apiRequest<PaginatedResponse<WarehouseItem>>("/inventory/warehouses?page=1&page_size=100", {
        accessToken,
        signal,
      }),
    enabled: Boolean(accessToken),
  });

  const prodQuery = useQuery({
    queryKey: ["inventory", "products", "dd"],
    queryFn: ({ signal }) =>
      apiRequest<PaginatedResponse<ProductItem>>("/inventory/products?page=1&page_size=100", {
        accessToken,
        signal,
      }),
    enabled: Boolean(accessToken),
  });

  const summaryQuery = useQuery({
    queryKey: ["inventory", "stock-summary"],
    queryFn: ({ signal }) =>
      apiRequest<StockSummaryResponse>("/inventory/stock-summary", { accessToken, signal }),
    enabled: Boolean(accessToken),
  });

  const moveMutation = useMutation({
    mutationFn: () =>
      apiRequest<unknown>("/inventory/movements", {
        method: "POST",
        accessToken,
        body: {
          movement_date: today,
          movement_type: movementType,
          warehouse_id: warehouseId,
          product_id: productId,
          quantity,
          reference,
        },
      }),
    onSuccess: () => {
      setFormError(null);
      setQuantity("1");
      setReference("");
      void queryClient.invalidateQueries({ queryKey: ["inventory", "stock-summary"] });
    },
    onError: (err: unknown) => {
      setFormError(err instanceof ApiError ? err.message : "Failed to record stock movement.");
    },
  });

  const lowCount = summaryQuery.data?.low_stock_count ?? 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{t("inventory.stockTitle")}</h1>
        <p className="text-sm text-muted-foreground">{t("inventory.stockSubtitle")}</p>
      </div>

      <section className="grid gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {t("inventory.totalValuation")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold tabular-nums">
              {formatBDT(summaryQuery.data?.total_valuation ?? "0.00", { banglaDigits })}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {t("inventory.lowStockAlerts")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="flex items-center gap-2 text-2xl font-bold tabular-nums">
              {lowCount > 0 ? <AlertTriangle className="h-5 w-5 text-destructive" /> : null}
              {banglaDigits ? toBanglaDigits(String(lowCount)) : String(lowCount)}
            </p>
          </CardContent>
        </Card>
      </section>

      {canMove ? (
        <Card>
          <CardHeader>
            <CardTitle>{t("inventory.recordMovement")}</CardTitle>
          </CardHeader>
          <CardContent>
            {formError ? (
              <div role="alert" className="mb-4 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {formError}
              </div>
            ) : null}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (!warehouseId || !productId) {
                  setFormError("Select both a warehouse and a product.");
                  return;
                }
                moveMutation.mutate();
              }}
              className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5"
            >
              <div>
                <Label htmlFor="m_type">{t("inventory.movementType")}</Label>
                <select
                  id="m_type"
                  className="flex h-10 w-full rounded-md border border-input bg-card px-3 text-sm"
                  value={movementType}
                  onChange={(e) => { setMovementType(e.target.value as MovementType); }}
                >
                  <option value="in">Stock IN (+)</option>
                  <option value="out">Stock OUT (-)</option>
                  <option value="adjustment">Adjustment (+/-)</option>
                </select>
              </div>
              <div>
                <Label htmlFor="m_wh">{t("inventory.warehouse")}</Label>
                <select
                  id="m_wh"
                  className="flex h-10 w-full rounded-md border border-input bg-card px-3 text-sm"
                  value={warehouseId}
                  onChange={(e) => { setWarehouseId(e.target.value); }}
                >
                  <option value="">-- Warehouse --</option>
                  {(whQuery.data?.items ?? []).map((w) => (
                    <option key={w.id} value={w.id}>
                      {w.code} — {w.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <Label htmlFor="m_prod">{t("inventory.product")}</Label>
                <select
                  id="m_prod"
                  className="flex h-10 w-full rounded-md border border-input bg-card px-3 text-sm"
                  value={productId}
                  onChange={(e) => { setProductId(e.target.value); }}
                >
                  <option value="">-- Product --</option>
                  {(prodQuery.data?.items ?? []).map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.sku} — {p.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <Label htmlFor="m_qty">{t("sales.qty")}</Label>
                <Input id="m_qty" inputMode="decimal" value={quantity} onChange={(e) => { setQuantity(e.target.value); }} />
              </div>
              <div>
                <Label htmlFor="m_ref">{t("accounting.reference")}</Label>
                <Input id="m_ref" placeholder="GRN-001" value={reference} onChange={(e) => { setReference(e.target.value); }} />
              </div>
              <div className="sm:col-span-2 lg:col-span-5">
                <Button type="submit" disabled={moveMutation.isPending}>
                  {t("inventory.recordMovement")}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>{t("inventory.stockTitle")}</CardTitle>
        </CardHeader>
        <CardContent>
          {summaryQuery.isLoading ? (
            <TableSkeleton rows={5} columns={6} />
          ) : summaryQuery.isError ? (
            <ErrorState
              title="Error"
              message={summaryQuery.error.message}
              retryLabel={t("dashboard.retry")}
              onRetry={() => void summaryQuery.refetch()}
            />
          ) : !summaryQuery.data || summaryQuery.data.items.length === 0 ? (
            <EmptyState title={t("inventory.emptyStock")} description={t("inventory.stockSubtitle")} />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-border text-xs uppercase text-muted-foreground">
                  <tr>
                    <th className="pb-2 pr-4">{t("inventory.sku")}</th>
                    <th className="pb-2 pr-4">{t("inventory.productName")}</th>
                    <th className="pb-2 pr-4">{t("inventory.warehouse")}</th>
                    <th className="pb-2 pr-4 text-right">{t("inventory.onHand")}</th>
                    <th className="pb-2 pr-4 text-right">{t("inventory.stockValue")}</th>
                    <th className="pb-2">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {summaryQuery.data.items.map((row) => (
                    <tr key={`${row.product_id}-${row.warehouse_id}`}>
                      <td className="py-2.5 pr-4 font-mono text-xs">{row.sku}</td>
                      <td className="py-2.5 pr-4 font-medium">{row.product_name}</td>
                      <td className="py-2.5 pr-4">{row.warehouse_code}</td>
                      <td className="py-2.5 pr-4 text-right tabular-nums">
                        {row.on_hand} {row.unit}
                      </td>
                      <td className="py-2.5 pr-4 text-right tabular-nums">
                        {formatBDT(row.stock_value, { banglaDigits })}
                      </td>
                      <td className="py-2.5">
                        <Badge variant={row.is_low_stock ? "secondary" : "default"}>
                          {row.is_low_stock ? t("inventory.lowStock") : t("inventory.inStock")}
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
