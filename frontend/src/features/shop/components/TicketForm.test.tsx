import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { TicketForm } from "@/features/shop/components/TicketForm";
import { axiosClient } from "@/shared/api/axiosClient";

vi.mock("@/shared/api/axiosClient", () => ({
  axiosClient: { get: vi.fn(), post: vi.fn() },
}));

const post = axiosClient.post as unknown as ReturnType<typeof vi.fn>;

function renderForm(onCreated = vi.fn()) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <TicketForm customerCode="C101" orderCode="ORD-1942" onCreated={onCreated} />
    </QueryClientProvider>,
  );
  return onCreated;
}

describe("TicketForm", () => {
  it("posts the ticket payload and reports the created ticket", async () => {
    const created = { code: "TCK-NEW", status: "open" };
    post.mockResolvedValueOnce({ data: created });
    const onCreated = renderForm();

    fireEvent.change(screen.getByLabelText("Subject"), { target: { value: "Cracked" } });
    fireEvent.change(screen.getByLabelText("What happened?"), { target: { value: "It broke" } });
    fireEvent.click(screen.getByRole("button", { name: "Raise ticket" }));

    await waitFor(() => expect(onCreated).toHaveBeenCalledWith(created));
    expect(post).toHaveBeenCalledWith("/api/shop/tickets", {
      customer_code: "C101",
      order_code: "ORD-1942",
      subject: "Cracked",
      body: "It broke",
      category: "damage",
    });
  });

  it("shows an error state when creation fails", async () => {
    post.mockRejectedValueOnce(new Error("boom"));
    renderForm();
    fireEvent.change(screen.getByLabelText("Subject"), { target: { value: "Cracked" } });
    fireEvent.change(screen.getByLabelText("What happened?"), { target: { value: "It broke" } });
    fireEvent.click(screen.getByRole("button", { name: "Raise ticket" }));
    expect(await screen.findByRole("alert")).toBeInTheDocument();
  });
});
