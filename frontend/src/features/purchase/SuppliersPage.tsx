import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import * as React from "react";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { z } from "zod";

import { EmptyState } from "@/components/states/EmptyState";
import { ErrorState } from "@/components/states/ErrorState";
import { TableSkeleton } from "@/components/states/TableSkeleton";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuthStore } from "@/features/auth/store";
import type { SupplierItem } from "@/features/purchase/types";
import { ApiError, apiRequest, type PaginatedResponse } from "@/lib/api";

const supplierSchema = z.object({
  code: z.string().trim().min(2).max(32),
  name: z.string().trim().min(2).max(255),
  phone: z.string().trim().max(32),
  email: z.string().trim().max(255),
  bin_no: z.string().trim().max(32),
  tin_no: z.string().trim().max(32),
});

type SupplierFormValues = z.infer<typeof supplierSchema>;

export function SuppliersPage(): React.JSX.Element {
  const { t } = useTranslation();
  const accessToken = useAuthStore((s) => s.accessToken);
  const permissions = useAuthStore((s) => s.permissions);
  const canWrite = permissions.includes("purchase.suppliers.write");
  const queryClient = useQueryClient();

  const [search, setSearch] = React.useState("");
  const [showForm, setShowForm] = React.useState(false);
  const [formError, setFormError] = React.useState<string | null>(null);

  const params = new URLSearchParams({ page: "1", page_size: "50", sort_by: "name", sort_dir: "asc" });
  if (search.trim()) params.set("search", search.trim());

  const suppliersQuery = useQuery({
    queryKey: ["purchase", "suppliers", search],
    queryFn: ({ signal }) =>
      apiRequest<PaginatedResponse<SupplierItem>>(`/purchase/suppliers?${params.toString()}`, {
        accessToken,
        signal,
      }),
    enabled: Boolean(accessToken),
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<SupplierFormValues>({
    resolver: zodResolver(supplierSchema),
    defaultValues: { code: "", name: "", phone: "", email: "", bin_no: "", tin_no: "" },
  });

  const createMutation = useMutation({
    mutationFn: (values: SupplierFormValues) =>
      apiRequest<SupplierItem>("/purchase/suppliers", {
        method: "POST",
        accessToken,
        body: values,
      }),
    onSuccess: () => {
      setShowForm(false);
      setFormError(null);
      reset();
      void queryClient.invalidateQueries({ queryKey: ["purchase", "suppliers"] });
    },
    onError: (err: unknown) => {
      setFormError(err instanceof ApiError ? err.message : "Failed to save supplier.");
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{t("purchase.suppliersTitle")}</h1>
          <p className="text-sm text-muted-foreground">{t("purchase.suppliersSubtitle")}</p>
        </div>
        {canWrite ? (
          <Button size="sm" onClick={() => { setShowForm((v) => !v); }}>
            <Plus className="h-4 w-4" aria-hidden="true" />
            {t("purchase.newSupplier")}
          </Button>
        ) : null}
      </div>

      {showForm && canWrite ? (
        <Card>
          <CardHeader>
            <CardTitle>{t("purchase.newSupplier")}</CardTitle>
          </CardHeader>
          <CardContent>
            {formError ? (
              <div role="alert" className="mb-4 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {formError}
              </div>
            ) : null}
            <form
              onSubmit={handleSubmit((vals) => { createMutation.mutate(vals); })}
              className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
            >
              <div className="space-y-1">
                <Label htmlFor="sup_code">{t("purchase.supplierCode")}</Label>
                <Input id="sup_code" placeholder="SUP-001" {...register("code")} />
                {errors.code ? <p className="text-xs text-destructive">{errors.code.message}</p> : null}
              </div>
              <div className="space-y-1">
                <Label htmlFor="sup_name">{t("purchase.supplierName")}</Label>
                <Input id="sup_name" placeholder="Meghna Supplies Ltd." {...register("name")} />
                {errors.name ? <p className="text-xs text-destructive">{errors.name.message}</p> : null}
              </div>
              <div className="space-y-1">
                <Label htmlFor="sup_phone">{t("sales.phone")}</Label>
                <Input id="sup_phone" placeholder="+8801811000000" {...register("phone")} />
              </div>
              <div className="space-y-1">
                <Label htmlFor="sup_email">{t("sales.email")}</Label>
                <Input id="sup_email" type="email" placeholder="billing@meghna.com.bd" {...register("email")} />
              </div>
              <div className="space-y-1">
                <Label htmlFor="sup_bin">{t("sales.binNo")}</Label>
                <Input id="sup_bin" placeholder="009876543-0201" {...register("bin_no")} />
              </div>
              <div className="space-y-1">
                <Label htmlFor="sup_tin">{t("sales.tinNo")}</Label>
                <Input id="sup_tin" placeholder="987654321012" {...register("tin_no")} />
              </div>
              <div className="flex gap-2 sm:col-span-2 lg:col-span-3">
                <Button type="submit" disabled={createMutation.isPending}>
                  {t("purchase.saveSupplier")}
                </Button>
                <Button variant="outline" onClick={() => { setShowForm(false); }}>
                  {t("accounting.cancel")}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader>
          <Input
            className="max-w-xs"
            placeholder={t("accounting.searchPlaceholder")}
            value={search}
            onChange={(e) => { setSearch(e.target.value); }}
          />
        </CardHeader>
        <CardContent>
          {suppliersQuery.isLoading ? (
            <TableSkeleton rows={5} columns={5} />
          ) : suppliersQuery.isError ? (
            <ErrorState
              title={t("purchase.suppliersErrorTitle")}
              message={suppliersQuery.error.message}
              retryLabel={t("dashboard.retry")}
              onRetry={() => void suppliersQuery.refetch()}
            />
          ) : !suppliersQuery.data || suppliersQuery.data.items.length === 0 ? (
            <EmptyState
              title={t("purchase.suppliersEmptyTitle")}
              description={t("purchase.suppliersEmptyDesc")}
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-border text-xs uppercase text-muted-foreground">
                  <tr>
                    <th className="pb-2 pr-4">{t("purchase.supplierCode")}</th>
                    <th className="pb-2 pr-4">{t("purchase.supplierName")}</th>
                    <th className="pb-2 pr-4">{t("sales.phone")}</th>
                    <th className="pb-2 pr-4">{t("sales.binNo")}</th>
                    <th className="pb-2">{t("sales.tinNo")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {suppliersQuery.data.items.map((s) => (
                    <tr key={s.id}>
                      <td className="py-2.5 pr-4 font-mono text-xs">{s.code}</td>
                      <td className="py-2.5 pr-4 font-medium">{s.name}</td>
                      <td className="py-2.5 pr-4">{s.phone || "—"}</td>
                      <td className="py-2.5 pr-4 font-mono text-xs">{s.bin_no || "—"}</td>
                      <td className="py-2.5 font-mono text-xs">{s.tin_no || "—"}</td>
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
