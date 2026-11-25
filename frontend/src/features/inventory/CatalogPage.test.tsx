import "@/i18n";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { useAuthStore } from "@/features/auth/store";
import { CatalogPage } from "@/features/inventory/CatalogPage";

describe("CatalogPage", () => {
  it("renders empty states for warehouses and products", async () => {
    useAuthStore.setState({
      accessToken: "test-token",
      permissions: ["inventory.products.read", "inventory.warehouses.read"],
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
        <CatalogPage />
      </QueryClientProvider>,
    );

    expect(await screen.findByText(/no warehouses yet/i)).toBeInTheDocument();
    expect(await screen.findByText(/no products yet/i)).toBeInTheDocument();
    vi.unstubAllGlobals();
  });
});
