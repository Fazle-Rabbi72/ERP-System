import "@/i18n";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { useAuthStore } from "@/features/auth/store";
import { CustomersPage } from "@/features/sales/CustomersPage";

describe("CustomersPage", () => {
  it("renders empty state when tenant has no customers", async () => {
    useAuthStore.setState({
      accessToken: "test-token",
      permissions: ["sales.customers.read", "sales.customers.write"],
    });
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve({
            items: [],
            meta: { page: 1, page_size: 50, total: 0, total_pages: 0, has_next: false, has_prev: false },
          }),
      }),
    );

    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <CustomersPage />
      </QueryClientProvider>,
    );

    expect(await screen.findByText(/no customers yet/i)).toBeInTheDocument();
    vi.unstubAllGlobals();
  });
});
