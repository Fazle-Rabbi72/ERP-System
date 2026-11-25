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
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { AccountItem, AccountType } from "@/features/accounting/types";
import { useAuthStore } from "@/features/auth/store";
import { ApiError, apiRequest, type PaginatedResponse } from "@/lib/api";

const accountSchema = z.object({
  code: z.string().trim().min(2).max(32),
  name: z.string().trim().min(2).max(255),
  account_type: z.enum(["asset", "liability", "equity", "revenue", "expense"]),
  is_group: z.boolean(),
  description: z.string().trim().max(500),
});

type AccountFormValues = z.infer<typeof accountSchema>;

const ACCOUNT_TYPES: AccountType[] = ["asset", "liability", "equity", "revenue", "expense"];

export function AccountsPage(): React.JSX.Element {
  const { t } = useTranslation();
  const accessToken = useAuthStore((s) => s.accessToken);
  const permissions = useAuthStore((s) => s.permissions);
  const canWrite = permissions.includes("accounting.accounts.write");
  const queryClient = useQueryClient();

  const [typeFilter, setTypeFilter] = React.useState<string>("");
  const [search, setSearch] = React.useState<string>("");
  const [showForm, setShowForm] = React.useState(false);
  const [formError, setFormError] = React.useState<string | null>(null);

  const queryParams = new URLSearchParams({ page: "1", page_size: "100", sort_by: "code", sort_dir: "asc" });
  if (typeFilter) queryParams.set("account_type", typeFilter);
  if (search.trim()) queryParams.set("search", search.trim());

  const accountsQuery = useQuery({
    queryKey: ["accounting", "accounts", typeFilter, search],
    queryFn: ({ signal }) =>
      apiRequest<PaginatedResponse<AccountItem>>(`/accounting/accounts?${queryParams.toString()}`, {
        accessToken,
        signal,
      }),
    enabled: Boolean(accessToken),
  });

  const seedMutation = useMutation({
    mutationFn: () =>
      apiRequest<{ created_count: number; total_accounts: number }>(
        "/accounting/accounts/seed-default",
        { method: "POST", accessToken },
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["accounting", "accounts"] });
    },
  });

  const createMutation = useMutation({
    mutationFn: (values: AccountFormValues) =>
      apiRequest<AccountItem>("/accounting/accounts", {
        method: "POST",
        accessToken,
        body: values,
      }),
    onSuccess: () => {
      setShowForm(false);
      setFormError(null);
      reset();
      void queryClient.invalidateQueries({ queryKey: ["accounting", "accounts"] });
    },
    onError: (err: unknown) => {
      setFormError(err instanceof ApiError ? err.message : "Failed to save account.");
    },
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<AccountFormValues>({
    resolver: zodResolver(accountSchema),
    defaultValues: { code: "", name: "", account_type: "asset", is_group: false, description: "" },
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{t("accounting.accountsTitle")}</h1>
          <p className="text-sm text-muted-foreground">{t("accounting.accountsSubtitle")}</p>
        </div>
        {canWrite ? (
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={seedMutation.isPending}
              onClick={() => { seedMutation.mutate(); }}
            >
              {seedMutation.isPending ? t("accounting.seeding") : t("accounting.seedDefault")}
            </Button>
            <Button size="sm" onClick={() => { setShowForm((v) => !v); }}>
              <Plus className="h-4 w-4" aria-hidden="true" />
              {t("accounting.newAccount")}
            </Button>
          </div>
        ) : null}
      </div>

      {showForm && canWrite ? (
        <Card>
          <CardHeader>
            <CardTitle>{t("accounting.newAccount")}</CardTitle>
          </CardHeader>
          <CardContent>
            {formError ? (
              <div role="alert" className="mb-4 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {formError}
              </div>
            ) : null}
            <form
              onSubmit={handleSubmit((vals) => { createMutation.mutate(vals); })}
              className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
            >
              <div className="space-y-1">
                <Label htmlFor="acc_code">{t("accounting.code")}</Label>
                <Input id="acc_code" placeholder="1130" {...register("code")} />
                {errors.code ? <p className="text-xs text-destructive">{errors.code.message}</p> : null}
              </div>
              <div className="space-y-1">
                <Label htmlFor="acc_name">{t("accounting.name")}</Label>
                <Input id="acc_name" placeholder="bKash Merchant Account" {...register("name")} />
                {errors.name ? <p className="text-xs text-destructive">{errors.name.message}</p> : null}
              </div>
              <div className="space-y-1">
                <Label htmlFor="acc_type">{t("accounting.type")}</Label>
                <select
                  id="acc_type"
                  className="flex h-10 w-full rounded-md border border-input bg-card px-3 text-sm"
                  {...register("account_type")}
                >
                  {ACCOUNT_TYPES.map((tp) => (
                    <option key={tp} value={tp}>
                      {tp.toUpperCase()}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex items-end gap-2">
                <label className="flex items-center gap-2 pb-2 text-sm">
                  <input type="checkbox" {...register("is_group")} />
                  {t("accounting.group")}
                </label>
              </div>
              <div className="flex gap-2 sm:col-span-2 lg:col-span-4">
                <Button type="submit" disabled={createMutation.isPending}>
                  {t("accounting.saveAccount")}
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
          <div className="flex flex-wrap items-center gap-3">
            <Input
              className="max-w-xs"
              placeholder={t("accounting.searchPlaceholder")}
              value={search}
              onChange={(e) => { setSearch(e.target.value); }}
            />
            <select
              aria-label={t("accounting.type")}
              className="h-10 rounded-md border border-input bg-card px-3 text-sm"
              value={typeFilter}
              onChange={(e) => { setTypeFilter(e.target.value); }}
            >
              <option value="">{t("accounting.allTypes")}</option>
              {ACCOUNT_TYPES.map((tp) => (
                <option key={tp} value={tp}>
                  {tp.toUpperCase()}
                </option>
              ))}
            </select>
          </div>
        </CardHeader>
        <CardContent>
          {accountsQuery.isLoading ? (
            <TableSkeleton rows={6} columns={5} />
          ) : accountsQuery.isError ? (
            <ErrorState
              title={t("accounting.accountsErrorTitle")}
              message={accountsQuery.error.message}
              retryLabel={t("dashboard.retry")}
              onRetry={() => void accountsQuery.refetch()}
            />
          ) : !accountsQuery.data || accountsQuery.data.items.length === 0 ? (
            <EmptyState
              title={t("accounting.accountsEmptyTitle")}
              description={t("accounting.accountsEmptyDesc")}
              action={
                canWrite ? (
                  <Button onClick={() => { seedMutation.mutate(); }}>
                    {t("accounting.seedDefault")}
                  </Button>
                ) : undefined
              }
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-border text-xs uppercase text-muted-foreground">
                  <tr>
                    <th className="pb-2 pr-4">{t("accounting.code")}</th>
                    <th className="pb-2 pr-4">{t("accounting.name")}</th>
                    <th className="pb-2 pr-4">{t("accounting.type")}</th>
                    <th className="pb-2 pr-4">{t("accounting.normalBalance")}</th>
                    <th className="pb-2">Kind</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {accountsQuery.data.items.map((acc) => (
                    <tr key={acc.id} className={acc.is_group ? "bg-muted/40 font-semibold" : ""}>
                      <td className="py-2.5 pr-4 font-mono text-xs">{acc.code}</td>
                      <td className="py-2.5 pr-4">{acc.name}</td>
                      <td className="py-2.5 pr-4 uppercase text-xs">{acc.account_type}</td>
                      <td className="py-2.5 pr-4 uppercase text-xs">{acc.normal_balance}</td>
                      <td className="py-2.5">
                        <Badge variant={acc.is_group ? "default" : "secondary"}>
                          {acc.is_group ? t("accounting.group") : t("accounting.ledger")}
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
