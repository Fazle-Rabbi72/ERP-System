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
import type { CustomerItem } from "@/features/sales/types";
import { ApiError, apiRequest, type PaginatedResponse } from "@/lib/api";

const customerSchema = z.object({
  code: z.string().trim().min(2).max(32),
  name: z.string().trim().min(2).max(255),
  phone: z.string().trim().max(32),
  email: z.string().trim().max(255),
  bin_no: z.string().trim().max(32),
  tin_no: z.string().trim().max(32),
});

type CustomerFormValues = z.infer<typeof customerSchema>;

export function CustomersPage(): React.JSX.Element {
  const { t } = useTranslation();
  const accessToken = useAuthStore((s) => s.accessToken);
  const permissions = useAuthStore((s) => s.permissions);
  const canWrite = permissions.includes("sales.customers.write");
  const queryClient = useQueryClient();

  const [search, setSearch] = React.useState("");
  const [showForm, setShowForm] = React.useState(false);
  const [formError, setFormError] = React.useState<string | null>(null);

  const params = new URLSearchParams({ page: "1", page_size: "50", sort_by: "name", sort_dir: "asc" });
  if (search.trim()) params.set("search", search.trim());

  const customersQuery = useQuery({
    queryKey: ["sales", "customers", search],
    queryFn: ({ signal }) =>
      apiRequest<PaginatedResponse<CustomerItem>>(`/sales/customers?${params.toString()}`, {
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
  } = useForm<CustomerFormValues>({
    resolver: zodResolver(customerSchema),
    defaultValues: { code: "", name: "", phone: "", email: "", bin_no: "", tin_no: "" },
  });

  const createMutation = useMutation({
    mutationFn: (values: CustomerFormValues) =>
      apiRequest<CustomerItem>("/sales/customers", {
        method: "POST",
        accessToken,
        body: values,
      }),
    onSuccess: () => {
      setShowForm(false);
      setFormError(null);
      reset();
      void queryClient.invalidateQueries({ queryKey: ["sales", "customers"] });
    },
    onError: (err: unknown) => {
      setFormError(err instanceof ApiError ? err.message : "Failed to save customer.");
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{t("sales.customersTitle")}</h1>
          <p className="text-sm text-muted-foreground">{t("sales.customersSubtitle")}</p>
        </div>
        {canWrite ? (
          <Button size="sm" onClick={() => { setShowForm((v) => !v); }}>
            <Plus className="h-4 w-4" aria-hidden="true" />
            {t("sales.newCustomer")}
          </Button>
        ) : null}
      </div>

      {showForm && canWrite ? (
        <Card>
          <CardHeader>
            <CardTitle>{t("sales.newCustomer")}</CardTitle>
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
                <Label htmlFor="cust_code">{t("sales.customerCode")}</Label>
                <Input id="cust_code" placeholder="CUST-001" {...register("code")} />
                {errors.code ? <p className="text-xs text-destructive">{errors.code.message}</p> : null}
              </div>
              <div className="space-y-1">
                <Label htmlFor="cust_name">{t("sales.customerName")}</Label>
                <Input id="cust_name" placeholder="Padma Traders Ltd." {...register("name")} />
                {errors.name ? <p className="text-xs text-destructive">{errors.name.message}</p> : null}
              </div>
              <div className="space-y-1">
                <Label htmlFor="cust_phone">{t("sales.phone")}</Label>
                <Input id="cust_phone" placeholder="+8801711000000" {...register("phone")} />
              </div>
              <div className="space-y-1">
                <Label htmlFor="cust_email">{t("sales.email")}</Label>
                <Input id="cust_email" type="email" placeholder="accounts@padma.com.bd" {...register("email")} />
              </div>
              <div className="space-y-1">
                <Label htmlFor="cust_bin">{t("sales.binNo")}</Label>
                <Input id="cust_bin" placeholder="001234567-0101" {...register("bin_no")} />
              </div>
              <div className="space-y-1">
                <Label htmlFor="cust_tin">{t("sales.tinNo")}</Label>
                <Input id="cust_tin" placeholder="123456789012" {...register("tin_no")} />
              </div>
              <div className="flex gap-2 sm:col-span-2 lg:col-span-3">
                <Button type="submit" disabled={createMutation.isPending}>
                  {t("sales.saveCustomer")}
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
          {customersQuery.isLoading ? (
            <TableSkeleton rows={5} columns={5} />
          ) : customersQuery.isError ? (
            <ErrorState
              title={t("sales.customersErrorTitle")}
              message={customersQuery.error.message}
              retryLabel={t("dashboard.retry")}
              onRetry={() => void customersQuery.refetch()}
            />
          ) : !customersQuery.data || customersQuery.data.items.length === 0 ? (
            <EmptyState
              title={t("sales.customersEmptyTitle")}
              description={t("sales.customersEmptyDesc")}
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-border text-xs uppercase text-muted-foreground">
                  <tr>
                    <th className="pb-2 pr-4">{t("sales.customerCode")}</th>
                    <th className="pb-2 pr-4">{t("sales.customerName")}</th>
                    <th className="pb-2 pr-4">{t("sales.phone")}</th>
                    <th className="pb-2 pr-4">{t("sales.binNo")}</th>
                    <th className="pb-2">{t("sales.tinNo")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {customersQuery.data.items.map((c) => (
                    <tr key={c.id}>
                      <td className="py-2.5 pr-4 font-mono text-xs">{c.code}</td>
                      <td className="py-2.5 pr-4 font-medium">{c.name}</td>
                      <td className="py-2.5 pr-4">{c.phone || "—"}</td>
                      <td className="py-2.5 pr-4 font-mono text-xs">{c.bin_no || "—"}</td>
                      <td className="py-2.5 font-mono text-xs">{c.tin_no || "—"}</td>
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
