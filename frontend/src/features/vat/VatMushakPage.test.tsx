import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type * as React from "react";
import { describe, expect, it, vi } from "vitest";

import { useAuthStore } from "@/features/auth/store";
import { VatMushakPage } from "@/features/vat/VatMushakPage";
import "@/i18n";
import * as api from "@/lib/api";

function renderWithQuery(ui: React.ReactElement): void {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe("VatMushakPage", () => {
  it("renders Mushak 9.1 summary with advisory note and switches to Mushak 6.2 + 6.3", async () => {
    useAuthStore.setState({
      accessToken: "test-token",
      permissions: ["vat.reports.read", "vat.rates.read", "vat.rates.write"],
      banglaDigits: false,
    });

    const spy = vi.spyOn(api, "apiRequest").mockImplementation((path: string) => {
      if (path.startsWith("/vat/mushak/9-1")) {
        return Promise.resolve({
          date_from: null,
          date_to: null,
          total_sales_taxable: "200000.00",
          total_output_vat: "30000.00",
          total_purchase_taxable: "100000.00",
          total_input_vat: "15000.00",
          net_vat_payable: "15000.00",
          carry_forward_credit: "0.00",
          total_vds_payable: "5000.00",
          total_tds_payable: "3000.00",
          advisory_note: "Verify final statutory return figures with your NBR tax advisor.",
        });
      }
      if (path.startsWith("/vat/mushak/6-2")) {
        return Promise.resolve({
          date_from: null,
          date_to: null,
          items: [
            {
              invoice_id: "inv-1",
              invoice_no: "INV-2026-0001",
              invoice_date: "2026-11-25",
              customer_name: "Dhaka Retail Ltd",
              customer_bin: "001234567-0101",
              taxable_value: "200000.00",
              output_vat: "30000.00",
              grand_total: "230000.00",
            },
          ],
          total_taxable_value: "200000.00",
          total_output_vat: "30000.00",
          total_grand_total: "230000.00",
        });
      }
      if (path === "/vat/mushak/6-3/inv-1") {
        return Promise.resolve({
          invoice_id: "inv-1",
          invoice_no: "INV-2026-0001",
          invoice_date: "2026-11-25",
          seller_name: "Nexzen Demo Ltd",
          customer_name: "Dhaka Retail Ltd",
          customer_bin: "001234567-0101",
          customer_address: "Gulshan, Dhaka",
          lines: [
            {
              line_no: 1,
              description: "Enterprise License",
              quantity: "2",
              unit_price: "100000.00",
              vat_rate_percent: "15.00",
              line_subtotal: "200000.00",
              line_vat: "30000.00",
              line_total: "230000.00",
            },
          ],
          subtotal: "200000.00",
          vat_total: "30000.00",
          grand_total: "230000.00",
        });
      }
      return Promise.resolve({ items: [], total: 0, page: 1, page_size: 100 });
    });

    renderWithQuery(<VatMushakPage />);

    await waitFor(() => {
      expect(
        screen.getByText(/Verify final statutory return figures with your NBR tax advisor/i),
      ).toBeInTheDocument();
    });
    expect(screen.getByText(/30,000\.00/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: /6\.2/ }));

    await waitFor(() => {
      expect(screen.getByText("INV-2026-0001")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /6\.3/ }));

    await waitFor(() => {
      expect(screen.getByText("Enterprise License")).toBeInTheDocument();
    });

    spy.mockRestore();
  });
});
