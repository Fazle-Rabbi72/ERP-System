import "@/i18n";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AccountsPage } from "@/features/accounting/AccountsPage";
import { useAuthStore } from "@/features/auth/store";

describe("AccountsPage", () => {
  it("renders empty state with Seed Default BD COA button when tenant has no accounts", async () => {
    useAuthStore.setState({
      accessToken: "test-token",
      permissions: ["accounting.accounts.read", "accounting.accounts.write"],
    });
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: () =>
          Promise.resolve({
            items: [],
            meta: { page: 1, page_size: 100, total: 0, total_pages: 0, has_next: false, has_prev: false },
          }),
      }),
    );

    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <AccountsPage />
      </QueryClientProvider>,
    );

    expect(await screen.findByText(/no accounts configured yet/i)).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /seed default bd coa/i }).length).toBeGreaterThan(0);

    vi.unstubAllGlobals();
  });
});
