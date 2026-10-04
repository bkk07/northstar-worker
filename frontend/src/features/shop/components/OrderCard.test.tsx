import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { OrderCard } from "@/features/shop/components/OrderCard";
import type { OrderRead } from "@/features/shop/types";

const ORDER: OrderRead = {
  id: "11111111-2222-3333-4444-555555555555",
  code: "ORD-1942",
  customer_id: "22222222-2222-3333-4444-555555555555",
  status: "delivered",
  total_paise: 8500000,
  paid_paise: 8500000,
  placed_at: "2026-09-28T00:00:00Z",
  delivered_at: "2026-09-29T00:00:00Z",
  items: [],
};

describe("OrderCard", () => {
  it("renders code, status, and formatted totals with a detail link", () => {
    render(
      <MemoryRouter>
        <OrderCard order={ORDER} />
      </MemoryRouter>,
    );
    expect(screen.getByRole("article", { name: "Order ORD-1942" })).toBeInTheDocument();
    // Total and Paid are equal in the fixture, so the amount appears twice.
    expect(screen.getAllByText("₹85,000.00")).toHaveLength(2);
    expect(screen.getByRole("link", { name: "ORD-1942" })).toHaveAttribute(
      "href",
      "/shop/orders/ORD-1942",
    );
  });
});
