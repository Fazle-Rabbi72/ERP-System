import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { EmptyState } from "@/components/states/EmptyState";
import { ErrorState } from "@/components/states/ErrorState";
import { TableSkeleton } from "@/components/states/TableSkeleton";

describe("Reusable UI state components", () => {
  it("renders accessible loading status for TableSkeleton", () => {
    render(<TableSkeleton rows={3} columns={2} />);
    expect(screen.getByRole("status", { name: /loading data/i })).toBeInTheDocument();
  });

  it("renders EmptyState title and description", () => {
    render(<EmptyState title="No invoices" description="Create your first invoice." />);
    expect(screen.getByText("No invoices")).toBeInTheDocument();
    expect(screen.getByText("Create your first invoice.")).toBeInTheDocument();
  });

  it("renders accessible ErrorState alert and invokes retry", async () => {
    const user = userEvent.setup();
    const onRetry = vi.fn();
    render(
      <ErrorState
        title="Load failed"
        message="Unable to reach the server."
        retryLabel="Retry now"
        onRetry={onRetry}
      />,
    );
    expect(screen.getByRole("alert")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Retry now" }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});
