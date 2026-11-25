import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
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
import type { EmployeeItem, PaginatedEmployees } from "@/features/hr/types";
import { apiRequest } from "@/lib/api";
import { formatBDT } from "@/lib/format";

export function EmployeesPage(): React.JSX.Element {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const accessToken = useAuthStore((s) => s.accessToken);
  const permissions = useAuthStore((s) => s.permissions);
  const banglaDigits = useAuthStore((s) => s.banglaDigits);

  const canWrite = permissions.includes("hr.employees.write");
  const [search, setSearch] = React.useState("");
  const [showForm, setShowForm] = React.useState(false);

  const [employeeCode, setEmployeeCode] = React.useState("");
  const [fullName, setFullName] = React.useState("");
  const [designation, setDesignation] = React.useState("");
  const [department, setDepartment] = React.useState("");
  const [phone, setPhone] = React.useState("");
  const [nidNo, setNidNo] = React.useState("");
  const [tinNo, setTinNo] = React.useState("");
  const [joinDate, setJoinDate] = React.useState(new Date().toISOString().slice(0, 10));
  const [basicSalary, setBasicSalary] = React.useState("30000.00");
  const [houseRent, setHouseRent] = React.useState("15000.00");
  const [medical, setMedical] = React.useState("3000.00");
  const [conveyance, setConveyance] = React.useState("2000.00");
  const [pfPercent, setPfPercent] = React.useState("0.00");
  const [taxAmount, setTaxAmount] = React.useState("0.00");
  const [formError, setFormError] = React.useState<string | null>(null);

  const qs = search.trim() ? `&search=${encodeURIComponent(search.trim())}` : "";
  const employeesQuery = useQuery({
    queryKey: ["hr", "employees", search],
    queryFn: ({ signal }) =>
      apiRequest<PaginatedEmployees>(`/hr/employees?page=1&page_size=100${qs}`, {
        accessToken,
        signal,
      }),
    enabled: Boolean(accessToken),
  });

  const createMutation = useMutation({
    mutationFn: () =>
      apiRequest<EmployeeItem>("/hr/employees", {
        method: "POST",
        accessToken,
        body: {
          employee_code: employeeCode.trim().toUpperCase(),
          full_name: fullName.trim(),
          designation: designation.trim(),
          department: department.trim(),
          phone: phone.trim(),
          nid_no: nidNo.trim(),
          tin_no: tinNo.trim(),
          join_date: joinDate,
          basic_salary: basicSalary,
          house_rent_allowance: houseRent || "0.00",
          medical_allowance: medical || "0.00",
          conveyance_allowance: conveyance || "0.00",
          other_allowance: "0.00",
          pf_deduction_percent: pfPercent || "0.00",
          tax_deduction_amount: taxAmount || "0.00",
        },
      }),
    onSuccess: () => {
      setEmployeeCode("");
      setFullName("");
      setDesignation("");
      setDepartment("");
      setPhone("");
      setNidNo("");
      setTinNo("");
      setFormError(null);
      setShowForm(false);
      void queryClient.invalidateQueries({ queryKey: ["hr", "employees"] });
    },
    onError: (err: Error) => {
      setFormError(err.message);
    },
  });

  const handleSubmit = (e: React.FormEvent): void => {
    e.preventDefault();
    setFormError(null);
    createMutation.mutate();
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{t("hr.employeesTitle")}</h1>
          <p className="text-sm text-muted-foreground">{t("hr.employeesSubtitle")}</p>
        </div>
        <div className="flex items-center gap-2">
          <Input
            placeholder={t("hr.searchEmployee")}
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
            }}
            className="w-56"
          />
          {canWrite ? (
            <Button
              size="sm"
              onClick={() => {
                setShowForm((v) => !v);
              }}
            >
              <Plus className="h-4 w-4" aria-hidden="true" />
              {t("hr.newEmployee")}
            </Button>
          ) : null}
        </div>
      </div>

      {showForm && canWrite ? (
        <Card>
          <CardHeader>
            <CardTitle>{t("hr.newEmployee")}</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div className="space-y-1">
                <Label htmlFor="emp-code">{t("hr.employeeCode")}</Label>
                <Input
                  id="emp-code"
                  required
                  placeholder="EMP-001"
                  value={employeeCode}
                  onChange={(e) => {
                    setEmployeeCode(e.target.value);
                  }}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="emp-name">{t("hr.fullName")}</Label>
                <Input
                  id="emp-name"
                  required
                  value={fullName}
                  onChange={(e) => {
                    setFullName(e.target.value);
                  }}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="emp-designation">{t("hr.designation")}</Label>
                <Input
                  id="emp-designation"
                  value={designation}
                  onChange={(e) => {
                    setDesignation(e.target.value);
                  }}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="emp-dept">{t("hr.department")}</Label>
                <Input
                  id="emp-dept"
                  value={department}
                  onChange={(e) => {
                    setDepartment(e.target.value);
                  }}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="emp-join">{t("hr.joinDate")}</Label>
                <Input
                  id="emp-join"
                  type="date"
                  required
                  value={joinDate}
                  onChange={(e) => {
                    setJoinDate(e.target.value);
                  }}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="emp-phone">{t("sales.phone")}</Label>
                <Input
                  id="emp-phone"
                  value={phone}
                  onChange={(e) => {
                    setPhone(e.target.value);
                  }}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="emp-nid">{t("hr.nidNo")}</Label>
                <Input
                  id="emp-nid"
                  value={nidNo}
                  onChange={(e) => {
                    setNidNo(e.target.value);
                  }}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="emp-tin">{t("sales.tinNo")}</Label>
                <Input
                  id="emp-tin"
                  value={tinNo}
                  onChange={(e) => {
                    setTinNo(e.target.value);
                  }}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="emp-basic">{t("hr.basicSalary")}</Label>
                <Input
                  id="emp-basic"
                  type="number"
                  step="0.01"
                  min="1"
                  required
                  value={basicSalary}
                  onChange={(e) => {
                    setBasicSalary(e.target.value);
                  }}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="emp-hra">{t("hr.houseRent")}</Label>
                <Input
                  id="emp-hra"
                  type="number"
                  step="0.01"
                  min="0"
                  value={houseRent}
                  onChange={(e) => {
                    setHouseRent(e.target.value);
                  }}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="emp-med">{t("hr.medical")}</Label>
                <Input
                  id="emp-med"
                  type="number"
                  step="0.01"
                  min="0"
                  value={medical}
                  onChange={(e) => {
                    setMedical(e.target.value);
                  }}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="emp-conv">{t("hr.conveyance")}</Label>
                <Input
                  id="emp-conv"
                  type="number"
                  step="0.01"
                  min="0"
                  value={conveyance}
                  onChange={(e) => {
                    setConveyance(e.target.value);
                  }}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="emp-pf">{t("hr.pfPercent")}</Label>
                <Input
                  id="emp-pf"
                  type="number"
                  step="0.01"
                  min="0"
                  max="50"
                  value={pfPercent}
                  onChange={(e) => {
                    setPfPercent(e.target.value);
                  }}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="emp-tax">{t("hr.monthlyTax")}</Label>
                <Input
                  id="emp-tax"
                  type="number"
                  step="0.01"
                  min="0"
                  value={taxAmount}
                  onChange={(e) => {
                    setTaxAmount(e.target.value);
                  }}
                />
              </div>
              <div className="flex items-end justify-end gap-2 sm:col-span-2">
                {formError ? <p className="text-sm text-destructive">{formError}</p> : null}
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    setShowForm(false);
                  }}
                >
                  {t("accounting.cancel")}
                </Button>
                <Button type="submit" disabled={createMutation.isPending}>
                  {t("hr.saveEmployee")}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>{t("hr.employeesTitle")}</CardTitle>
        </CardHeader>
        <CardContent>
          {employeesQuery.isLoading ? (
            <TableSkeleton rows={5} columns={6} />
          ) : employeesQuery.isError ? (
            <ErrorState
              title={t("hr.employeesError")}
              message={employeesQuery.error.message}
              retryLabel={t("dashboard.retry")}
              onRetry={() => void employeesQuery.refetch()}
            />
          ) : !employeesQuery.data || employeesQuery.data.items.length === 0 ? (
            <EmptyState
              title={t("hr.employeesEmptyTitle")}
              description={t("hr.employeesEmptyDesc")}
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="border-b border-border text-xs uppercase text-muted-foreground">
                  <tr>
                    <th className="pb-2 pr-4">{t("hr.employeeCode")}</th>
                    <th className="pb-2 pr-4">{t("hr.fullName")}</th>
                    <th className="pb-2 pr-4">{t("hr.designation")}</th>
                    <th className="pb-2 pr-4 text-right">{t("hr.basicSalary")}</th>
                    <th className="pb-2 pr-4 text-right">{t("hr.pfPercent")}</th>
                    <th className="pb-2 pr-4 text-right">{t("hr.monthlyTax")}</th>
                    <th className="pb-2">{t("hr.status")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {employeesQuery.data.items.map((emp) => (
                    <tr key={emp.id}>
                      <td className="py-2.5 pr-4 font-mono text-xs">{emp.employee_code}</td>
                      <td className="py-2.5 pr-4">
                        <div className="font-medium">{emp.full_name}</div>
                        {emp.department ? (
                          <div className="text-xs text-muted-foreground">{emp.department}</div>
                        ) : null}
                      </td>
                      <td className="py-2.5 pr-4">{emp.designation || "—"}</td>
                      <td className="py-2.5 pr-4 text-right tabular-nums">
                        {formatBDT(emp.basic_salary, { banglaDigits })}
                      </td>
                      <td className="py-2.5 pr-4 text-right tabular-nums">
                        {emp.pf_deduction_percent}%
                      </td>
                      <td className="py-2.5 pr-4 text-right tabular-nums">
                        {formatBDT(emp.tax_deduction_amount, { banglaDigits })}
                      </td>
                      <td className="py-2.5">
                        <Badge variant={emp.is_active ? "default" : "secondary"}>
                          {emp.is_active ? t("hr.active") : t("hr.inactive")}
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
