import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import * as React from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "@/components/layout/AppShell";
import { TableSkeleton } from "@/components/states/TableSkeleton";
import { AccountsPage } from "@/features/accounting/AccountsPage";
import { JournalsPage } from "@/features/accounting/JournalsPage";
import { TrialBalancePage } from "@/features/accounting/TrialBalancePage";
import { AuditLogsPage } from "@/features/audit/AuditLogsPage";
import { LoginPage } from "@/features/auth/LoginPage";
import { useAuthStore } from "@/features/auth/store";
import { DashboardPage } from "@/features/dashboard/DashboardPage";
import { EmployeesPage } from "@/features/hr/EmployeesPage";
import { PayrollPage } from "@/features/hr/PayrollPage";
import { CatalogPage } from "@/features/inventory/CatalogPage";
import { StockPage } from "@/features/inventory/StockPage";
import { BillsPage } from "@/features/purchase/BillsPage";
import { SuppliersPage } from "@/features/purchase/SuppliersPage";
import { FinancialStatementsPage } from "@/features/reports/FinancialStatementsPage";
import { CustomersPage } from "@/features/sales/CustomersPage";
import { InvoicesPage } from "@/features/sales/InvoicesPage";
import { VatMushakPage } from "@/features/vat/VatMushakPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function RequireAuth({ children }: { children: React.ReactElement }): React.JSX.Element {
  const accessToken = useAuthStore((s) => s.accessToken);
  const isRestoring = useAuthStore((s) => s.isRestoring);

  if (isRestoring) {
    return (
      <div className="mx-auto max-w-4xl p-8">
        <TableSkeleton rows={5} columns={3} />
      </div>
    );
  }
  if (!accessToken) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

export function App(): React.JSX.Element {
  const restoreSession = useAuthStore((s) => s.restoreSession);

  React.useEffect(() => {
    void restoreSession();
  }, [restoreSession]);

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            element={
              <RequireAuth>
                <AppShell />
              </RequireAuth>
            }
          >
            <Route path="/" element={<DashboardPage />} />
            <Route path="/accounting/accounts" element={<AccountsPage />} />
            <Route path="/accounting/journals" element={<JournalsPage />} />
            <Route path="/accounting/trial-balance" element={<TrialBalancePage />} />
            <Route path="/reports/statements" element={<FinancialStatementsPage />} />
            <Route path="/sales/customers" element={<CustomersPage />} />
            <Route path="/sales/invoices" element={<InvoicesPage />} />
            <Route path="/purchase/suppliers" element={<SuppliersPage />} />
            <Route path="/purchase/bills" element={<BillsPage />} />
            <Route path="/inventory/catalog" element={<CatalogPage />} />
            <Route path="/inventory/stock" element={<StockPage />} />
            <Route path="/vat/mushak" element={<VatMushakPage />} />
            <Route path="/hr/employees" element={<EmployeesPage />} />
            <Route path="/hr/payroll" element={<PayrollPage />} />
            <Route path="/audit-logs" element={<AuditLogsPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
