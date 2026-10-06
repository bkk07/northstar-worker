import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import ProductsPage from "./ProductsPage";

vi.mock("../api/catalogApi", () => ({
  listProducts: async () => [
    { sku: "HP-01", title: "Studio Headphones", category: "electronics", unit_paise: 250000, orders_count: 2 },
  ],
  getProduct: async () => ({
    product: { sku: "HP-01", title: "Studio Headphones" },
    policies: [{ rule_key: "P-REF-001", summary: "Auto-approve refunds up to ₹5,000", params: {}, version: 1 }],
  }),
  listPolicies: async () => [
    { rule_key: "P-REF-001", summary: "Auto-approve refunds up to ₹5,000", params: {}, version: 1 },
  ],
}));

function page() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <ProductsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ProductsPage", () => {
  it("lists products and expands their governing policies", async () => {
    page();
    await waitFor(() => {
      expect(screen.getByText("Studio Headphones")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole("button", { name: /Show policies/ }));
    await waitFor(() => {
      expect(screen.getByText(/Auto-approve refunds up to/)).toBeInTheDocument();
    });
    expect(screen.getByText("All policies")).toBeInTheDocument();
  });
});
