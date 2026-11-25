import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type * as React from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "@/components/layout/AppShell";
import { AccountsPage } from "@/features/accounting/AccountsPage";
import { JournalsPage } from "@/features/accounting/JournalsPage";
import { TrialBalancePage } from "@/features/accounting/TrialBalancePage";
import { AuditLogsPage } from "@/features/audit/AuditLogsPage";
import { LoginPage } from "@/features/auth/LoginPage";
import { useAuthStore } from "@/features/auth/store";
import { DashboardPage } from "@/features/dashboard/DashboardPage";
import { CustomersPage } from "@/features/sales/CustomersPage";
import { InvoicesPage } from "@/features/sales/InvoicesPage";

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
  if (!accessToken) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

export function App(): React.JSX.Element {
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
            <Route path="/sales/customers" element={<CustomersPage />} />
            <Route path="/sales/invoices" element={<InvoicesPage />} />
            <Route path="/audit-logs" element={<AuditLogsPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
