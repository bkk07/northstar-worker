import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ContextPanel } from "./ContextPanel";

vi.mock("@/features/shop/hooks/useShop", () => ({
  useTicket: (code?: string) => ({
    data: code
      ? {
          code,
          status: "open",
          subject: "Headphones refund",
          body: "Want my money back",
          category: "refund",
          order_id: "order-1",
        }
      : undefined,
    isPending: false,
  }),
}));

vi.mock("@/shared/api/axiosClient", () => ({
  axiosClient: {
    get: async () => ({
      data: {
        code: "ORD-1943",
        status: "delivered",
        total_paise: 250000,
        items: [
          {
            id: "item-1",
            sku: "HP-01",
            title: "Studio Headphones",
            qty: 1,
            unit_paise: 250000,
            category: "electronics",
          },
        ],
      },
    }),
  },
}));

vi.mock("../api/catalogApi", () => ({
  getProduct: async () => ({
    product: { sku: "HP-01", title: "Studio Headphones" },
    policies: [{ rule_key: "P-REF-001", summary: "Auto-approve refunds up to ₹5,000" }],
  }),
  listProducts: async () => [],
}));

vi.mock("@/features/worker/api/workerApi", () => ({
  listApprovals: async () => [],
}));

function panel() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <ContextPanel
        ticketCode="TCK-102"
        deciding={null}
        onAsk={vi.fn()}
        onSolve={vi.fn()}
        onDecide={vi.fn()}
      />
    </QueryClientProvider>,
  );
}

describe("ContextPanel", () => {
  it("shows ticket, order, product, and governing policy together", async () => {
    panel();
    await waitFor(() => {
      expect(screen.getByText("Headphones refund")).toBeInTheDocument();
    });
    await waitFor(() => {
      expect(screen.getByText("ORD-1943")).toBeInTheDocument();
    });
    expect(screen.getByText("Studio Headphones")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText(/Auto-approve refunds up to/)).toBeInTheDocument();
    });
  });
});
