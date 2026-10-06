import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { TicketRail } from "./TicketRail";

vi.mock("@/features/ops/tickets/hooks/useTickets", () => ({
  useTicketQueue: () => ({
    data: {
      items: [
        { code: "TCK-102", subject: "Headphones refund", status: "open" },
        { code: "TCK-101", subject: "Laptop screen", status: "resolved" },
      ],
      page: 1,
      page_size: 10,
      total: 2,
    },
    isPending: false,
    isError: false,
    refetch: vi.fn(),
  }),
}));

describe("TicketRail", () => {
  it("lists tickets and raises/selects/solves through callbacks", () => {
    const onSelect = vi.fn();
    const onSolve = vi.fn();
    const onRaise = vi.fn();
    render(
      <MemoryRouter>
        <TicketRail selected={null} onSelect={onSelect} onSolve={onSolve} onRaise={onRaise} />
      </MemoryRouter>,
    );
    expect(screen.getByText("TCK-102")).toBeInTheDocument();
    fireEvent.click(screen.getByText("TCK-102"));
    expect(onSelect).toHaveBeenCalledWith("TCK-102");
    fireEvent.click(screen.getAllByText("Solve with bot →")[0]);
    expect(onSolve).toHaveBeenCalledWith("TCK-102");
    fireEvent.click(screen.getByRole("button", { name: "Raise a ticket" }));
    expect(onRaise).toHaveBeenCalled();
  });

  it("filters the queue by the search box", () => {
    render(
      <MemoryRouter>
        <TicketRail selected={null} onSelect={vi.fn()} onSolve={vi.fn()} onRaise={vi.fn()} />
      </MemoryRouter>,
    );
    fireEvent.change(screen.getByPlaceholderText(/Search code/), {
      target: { value: "laptop" },
    });
    expect(screen.queryByText("TCK-102")).not.toBeInTheDocument();
    expect(screen.getByText("TCK-101")).toBeInTheDocument();
  });
});
