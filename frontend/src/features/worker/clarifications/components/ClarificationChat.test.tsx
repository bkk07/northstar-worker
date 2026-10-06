import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { ClarificationChatView } from "@/features/worker/clarifications/components/ClarificationChat";
import { axiosClient } from "@/shared/api/axiosClient";
import type { ClarificationRead } from "@/features/worker/types";

vi.mock("@/shared/api/axiosClient", () => ({
  axiosClient: { get: vi.fn(), post: vi.fn() },
}));

const post = axiosClient.post as unknown as ReturnType<typeof vi.fn>;

function providers(children: React.ReactNode) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={queryClient}>{children}</QueryClientProvider>);
}

const OPEN: ClarificationRead = {
  id: "c1",
  task_id: "t1",
  kind: "operator",
  question: "Replace or refund?",
  answer: null,
  answered_by: null,
  status: "pending",
  created_at: "2026-10-05T00:00:00.000Z",
};

const ANSWERED: ClarificationRead = {
  ...OPEN,
  id: "c2",
  question: "Which order?",
  answer: "ORD-1950",
  answered_by: "duty-ops",
  status: "answered",
};

describe("ClarificationChatView", () => {
  beforeEach(() => {
    post.mockClear();
  });
  it("shows the worker question and sends the operator answer", async () => {
    post.mockResolvedValueOnce({ data: { ...OPEN, status: "answered" } });
    providers(<ClarificationChatView items={[OPEN]} waiting />);

    expect(screen.getByText("Replace or refund?")).toBeInTheDocument();
    expect(screen.getByText("Awaiting your answer")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Answer"), { target: { value: "Replace it" } });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() =>
      expect(post).toHaveBeenCalledWith("/api/clarifications/c1/answer", {
        answer: "Replace it",
        answered_by: "duty-ops",
      }),
    );
    expect(await screen.findByText(/re-enters contract/)).toBeInTheDocument();
  });

  it("renders answered threads as history without a reply box", () => {
    providers(<ClarificationChatView items={[ANSWERED]} waiting={false} />);

    expect(screen.getByText("ORD-1950")).toBeInTheDocument();
    expect(screen.queryByLabelText("Answer")).not.toBeInTheDocument();
    expect(screen.getByText("Resolved")).toBeInTheDocument();
  });

  it("quick-fills draft the reply without sending", () => {
    providers(<ClarificationChatView items={[OPEN]} waiting />);

    fireEvent.click(
      screen.getByRole("button", { name: "Replace the damaged item on its order." }),
    );
    expect(screen.getByLabelText("Answer")).toHaveValue(
      "Replace the damaged item on its order.",
    );
    expect(post).not.toHaveBeenCalled();
  });
});
