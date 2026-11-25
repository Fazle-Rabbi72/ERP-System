import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type * as React from "react";
import { describe, expect, it, vi } from "vitest";

import { useAuthStore } from "@/features/auth/store";
import { PayrollPage } from "@/features/hr/PayrollPage";
import "@/i18n";
import * as api from "@/lib/api";

function renderWithQuery(ui: React.ReactElement): void {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe("PayrollPage", () => {
  it("lists payroll runs and displays itemized payslips with advisory note", async () => {
    useAuthStore.setState({
      accessToken: "test-token",
      permissions: ["hr.payroll.read", "hr.payroll.write", "hr.payroll.post"],
      banglaDigits: false,
    });

    const spy = vi.spyOn(api, "apiRequest").mockImplementation((path: string) => {
      if (path.startsWith("/hr/payroll-runs?")) {
        return Promise.resolve({
          items: [
            {
              id: "run-1",
              run_no: "PAY-2026-11",
              pay_year: 2026,
              pay_month: 11,
              status: "draft",
              total_gross: "160000.00",
              total_deductions: "13000.00",
              total_net_pay: "147000.00",
              journal_entry_id: null,
              notes: "Nov Salary",
              posted_at: null,
              created_at: "2026-11-25T00:00:00Z",
            },
          ],
          meta: { page: 1, page_size: 50, total: 1, total_pages: 1 },
        });
      }
      if (path === "/hr/payroll-runs/run-1") {
        return Promise.resolve({
          id: "run-1",
          run_no: "PAY-2026-11",
          pay_year: 2026,
          pay_month: 11,
          status: "draft",
          total_gross: "160000.00",
          total_deductions: "13000.00",
          total_net_pay: "147000.00",
          journal_entry_id: null,
          notes: "Nov Salary",
          posted_at: null,
          created_at: "2026-11-25T00:00:00Z",
          advisory_note: "Verify Bangladesh Labour Act compliance with your HR & tax advisor.",
          lines: [
            {
              id: "line-1",
              employee_id: "emp-1",
              employee_code: "EMP-001",
              employee_name: "Md. Rahim Uddin",
              designation: "Senior Engineer",
              basic_salary: "60000.00",
              allowances_total: "40000.00",
              gross_salary: "100000.00",
              pf_deduction: "6000.00",
              tax_deduction: "4000.00",
              other_deduction: "0.00",
              total_deductions: "10000.00",
              net_salary: "90000.00",
            },
          ],
        });
      }
      return Promise.resolve({ items: [] });
    });

    renderWithQuery(<PayrollPage />);

    await waitFor(() => {
      expect(screen.getByText("PAY-2026-11")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /payslips|পে-স্লিপ/i }));

    await waitFor(() => {
      expect(screen.getByText("Md. Rahim Uddin")).toBeInTheDocument();
    });
    expect(screen.getByText(/Bangladesh Labour Act/i)).toBeInTheDocument();

    spy.mockRestore();
  });
});
