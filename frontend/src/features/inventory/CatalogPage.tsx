import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import * as React from "react";
import { useTranslation } from "react-i18next";

import { EmptyState } from "@/components/states/EmptyState";
import { ErrorState } from "@/components/states/ErrorState";
import { TableSkeleton } from "@/components/states/TableSkeleton";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuthStore } from "@/features/auth/store";
import type { ProductItem, WarehouseItem } from "@/features/inventory/types";
import { ApiError, apiRequest, type PaginatedResponse } from "@/lib/api";
import { formatBDT } from "@/lib/format";

export function CatalogPage(): React.JSX.Element {
  const { t } = useTranslation();
  const accessToken = useAuthStore((s) => s.accessToken);
  const permissions = useAuthStore((s) => s.permissions);
  const banglaDigits = useAuthStore((s) => s.banglaDigits);
  const canWriteWh = permissions.includes("inventory.warehouses.write");
  const canWriteProd = permissions.includes("inventory.products.write");
  const queryClient = useQueryClient();

  const [whCode, setWhCode] = React.useState("");
  const [whName, setWhName] = React.useState("");
  const [whLoc, setWhLoc] = React.useState("");
  const [whError, setWhError] = React.useState<string | null>(null);

  const [sku, setSku] = React.useState("");
  const [prodName, setProdName] = React.useState("");
  const [unit, setUnit] = React.useState("pcs");
  const [unitCost, setUnitCost] = React.useState("0.00");
  const [salePrice, setSalePrice] = React.useState("0.00");
  const [reorder, setReorder] = React.useState("10.000");
  const [prodError, setProdError] = React.useState<string | null>(null);

  const whQuery = useQuery({
    queryKey: ["inventory", "warehouses"],
    queryFn: ({ signal }) =>
      apiRequest<PaginatedResponse<WarehouseItem>>("/inventory/warehouses?page=1&page_size=50", {
        accessToken,
        signal,
      }),
    enabled: Boolean(accessToken),
  });

  const prodQuery = useQuery({
    queryKey: ["inventory", "products"],
    queryFn: ({ signal }) =>
      apiRequest<PaginatedResponse<ProductItem>>("/inventory/products?page=1&page_size=50", {
        accessToken,
        signal,
      }),
    enabled: Boolean(accessToken),
  });

  const createWh = useMutation({
    mutationFn: () =>
      apiRequest<WarehouseItem>("/inventory/warehouses", {
        method: "POST",
        accessToken,
        body: { code: whCode, name: whName, location: whLoc },
      }),
    onSuccess: () => {
      setWhCode("");
      setWhName("");
      setWhLoc("");
      setWhError(null);
      void queryClient.invalidateQueries({ queryKey: ["inventory", "warehouses"] });
    },
    onError: (err: unknown) => {
      setWhError(err instanceof ApiError ? err.message : "Failed to save warehouse.");
    },
  });

  const createProd = useMutation({
    mutationFn: () =>
      apiRequest<ProductItem>("/inventory/products", {
        method: "POST",
        accessToken,
        body: {
          sku,
          name: prodName,
          unit,
          unit_cost: unitCost,
          sale_price: salePrice,
          reorder_level: reorder,
        },
      }),
    onSuccess: () => {
      setSku("");
      setProdName("");
      setUnitCost("0.00");
      setSalePrice("0.00");
      setProdError(null);
      void queryClient.invalidateQueries({ queryKey: ["inventory", "products"] });
    },
    onError: (err: unknown) => {
      setProdError(err instanceof ApiError ? err.message : "Failed to save product.");
    },
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{t("inventory.catalogTitle")}</h1>
        <p className="text-sm text-muted-foreground">{t("inventory.catalogSubtitle")}</p>
      </div>

      {/* Warehouses */}
      <Card>
        <CardHeader>
          <CardTitle>{t("inventory.warehouses")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {canWriteWh ? (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                createWh.mutate();
              }}
              className="grid gap-3 sm:grid-cols-4"
            >
              <div>
                <Label htmlFor="wh_code">{t("inventory.warehouseCode")}</Label>
                <Input id="wh_code" placeholder="WH-DHK" value={whCode} onChange={(e) => { setWhCode(e.target.value); }} />
              </div>
              <div>
                <Label htmlFor="wh_name">{t("inventory.warehouseName")}</Label>
                <Input id="wh_name" placeholder="Dhaka Central" value={whName} onChange={(e) => { setWhName(e.target.value); }} />
              </div>
              <div>
                <Label htmlFor="wh_loc">{t("inventory.location")}</Label>
                <Input id="wh_loc" placeholder="Tejgaon, Dhaka" value={whLoc} onChange={(e) => { setWhLoc(e.target.value); }} />
              </div>
              <div className="flex items-end">
                <Button type="submit" disabled={createWh.isPending} className="w-full">
                  <Plus className="h-4 w-4" aria-hidden="true" />
                  {t("inventory.newWarehouse")}
                </Button>
              </div>
              {whError ? <p role="alert" className="text-xs text-destructive sm:col-span-4">{whError}</p> : null}
            </form>
          ) : null}

          {whQuery.isLoading ? (
            <TableSkeleton rows={3} columns={3} />
          ) : whQuery.isError ? (
            <ErrorState title="Error" message={whQuery.error.message} onRetry={() => void whQuery.refetch()} />
          ) : !whQuery.data || whQuery.data.items.length === 0 ? (
            <EmptyState title={t("inventory.emptyWarehouses")} description={t("inventory.catalogSubtitle")} />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-border text-xs uppercase text-muted-foreground">
                  <tr>
                    <th className="pb-2 pr-4">{t("inventory.warehouseCode")}</th>
                    <th className="pb-2 pr-4">{t("inventory.warehouseName")}</th>
                    <th className="pb-2">{t("inventory.location")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {whQuery.data.items.map((w) => (
                    <tr key={w.id}>
                      <td className="py-2 pr-4 font-mono text-xs">{w.code}</td>
                      <td className="py-2 pr-4 font-medium">{w.name}</td>
                      <td className="py-2 text-muted-foreground">{w.location || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Products */}
      <Card>
        <CardHeader>
          <CardTitle>{t("inventory.products")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {canWriteProd ? (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                createProd.mutate();
              }}
              className="grid gap-3 sm:grid-cols-3 lg:grid-cols-6"
            >
              <div>
                <Label htmlFor="p_sku">{t("inventory.sku")}</Label>
                <Input id="p_sku" placeholder="PUMP-5HP" value={sku} onChange={(e) => { setSku(e.target.value); }} />
              </div>
              <div>
                <Label htmlFor="p_name">{t("inventory.productName")}</Label>
                <Input id="p_name" placeholder="5HP Pump" value={prodName} onChange={(e) => { setProdName(e.target.value); }} />
              </div>
              <div>
                <Label htmlFor="p_unit">{t("inventory.unit")}</Label>
                <Input id="p_unit" value={unit} onChange={(e) => { setUnit(e.target.value); }} />
              </div>
              <div>
                <Label htmlFor="p_cost">{t("inventory.unitCost")}</Label>
                <Input id="p_cost" inputMode="decimal" value={unitCost} onChange={(e) => { setUnitCost(e.target.value); }} />
              </div>
              <div>
                <Label htmlFor="p_sale">{t("inventory.salePrice")}</Label>
                <Input id="p_sale" inputMode="decimal" value={salePrice} onChange={(e) => { setSalePrice(e.target.value); }} />
              </div>
              <div>
                <Label htmlFor="p_reord">{t("inventory.reorderLevel")}</Label>
                <Input id="p_reord" inputMode="decimal" value={reorder} onChange={(e) => { setReorder(e.target.value); }} />
              </div>
              <div className="sm:col-span-3 lg:col-span-6">
                <Button type="submit" disabled={createProd.isPending}>
                  <Plus className="h-4 w-4" aria-hidden="true" />
                  {t("inventory.newProduct")}
                </Button>
              </div>
              {prodError ? <p role="alert" className="text-xs text-destructive sm:col-span-6">{prodError}</p> : null}
            </form>
          ) : null}

          {prodQuery.isLoading ? (
            <TableSkeleton rows={4} columns={5} />
          ) : prodQuery.isError ? (
            <ErrorState title="Error" message={prodQuery.error.message} onRetry={() => void prodQuery.refetch()} />
          ) : !prodQuery.data || prodQuery.data.items.length === 0 ? (
            <EmptyState title={t("inventory.emptyProducts")} description={t("inventory.catalogSubtitle")} />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-border text-xs uppercase text-muted-foreground">
                  <tr>
                    <th className="pb-2 pr-4">{t("inventory.sku")}</th>
                    <th className="pb-2 pr-4">{t("inventory.productName")}</th>
                    <th className="pb-2 pr-4">{t("inventory.unit")}</th>
                    <th className="pb-2 pr-4 text-right">{t("inventory.unitCost")}</th>
                    <th className="pb-2 pr-4 text-right">{t("inventory.salePrice")}</th>
                    <th className="pb-2 text-right">{t("inventory.reorderLevel")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {prodQuery.data.items.map((p) => (
                    <tr key={p.id}>
                      <td className="py-2 pr-4 font-mono text-xs">{p.sku}</td>
                      <td className="py-2 pr-4 font-medium">{p.name}</td>
                      <td className="py-2 pr-4">{p.unit}</td>
                      <td className="py-2 pr-4 text-right tabular-nums">
                        {formatBDT(p.unit_cost, { banglaDigits })}
                      </td>
                      <td className="py-2 pr-4 text-right tabular-nums">
                        {formatBDT(p.sale_price, { banglaDigits })}
                      </td>
                      <td className="py-2 text-right tabular-nums">{p.reorder_level}</td>
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
