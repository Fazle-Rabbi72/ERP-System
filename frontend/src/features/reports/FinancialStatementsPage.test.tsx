import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type * as React from "react";
import { describe, expect, it, vi } from "vitest";

import { useAuthStore } from "@/features/auth/store";
import { FinancialStatementsPage } from "@/features/reports/FinancialStatementsPage";
import "@/i18n";
import * as api from "@/lib/api";

function renderWithQuery(ui: React.ReactElement): void {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe("FinancialStatementsPage", () => {
  it("renders Profit & Loss and switches to balanced Balance Sheet", async () => {
    useAuthStore.setState({
      accessToken: "test-token",
      permissions: ["accounting.reports.read"],
      banglaDigits: false,
    });

    const spy = vi.spyOn(api, "apiRequest").mockImplementation((path: string) => {
      if (path.startsWith("/reports/profit-and-loss")) {
        return Promise.resolve({
          date_from: null,
          date_to: null,
          revenue_lines: [
            { account_id: "a1", code: "4100", name: "Sales Revenue", amount: "150000.00" },
          ],
          expense_lines: [
            { account_id: "a2", code: "5200", name: "Salaries & Wages", amount: "60000.00" },
          ],
          total_revenue: "150000.00",
          total_expense: "60000.00",
          net_profit: "90000.00",
        });
      }
      if (path.startsWith("/reports/balance-sheet")) {
        return Promise.resolve({
          as_of_date: null,
          asset_lines: [
            { account_id: "a3", code: "1110", name: "Cash in Hand", amount: "90000.00" },
          ],
          liability_lines: [],
          equity_lines: [],
          current_earnings: "90000.00",
          total_assets: "90000.00",
          total_liabilities: "0.00",
          total_equity: "90000.00",
          total_liabilities_and_equity: "90000.00",
          is_balanced: true,
        });
      }
      return Promise.resolve({});
    });

    renderWithQuery(<FinancialStatementsPage />);

    await waitFor(() => {
      expect(screen.getByText("Sales Revenue")).toBeInTheDocument();
    });
    expect(screen.getByText(/90,000\.00/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: /Balance Sheet|ব্যালেন্স শিট/i }));

    await waitFor(() => {
      expect(screen.getByText("Cash in Hand")).toBeInTheDocument();
    });

    spy.mockRestore();
  });
});
