import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import {
  ApprovalQueueView,
  ClarificationQueueView,
} from "@/features/worker/approvals/components/ApprovalQueue";
import { axiosClient } from "@/shared/api/axiosClient";
import type { ApprovalRead, ClarificationRead } from "@/features/worker/types";

vi.mock("@/shared/api/axiosClient", () => ({
  axiosClient: { get: vi.fn(), post: vi.fn() },
}));

const post = axiosClient.post as unknown as ReturnType<typeof vi.fn>;

function providers(children: React.ReactNode) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={queryClient}>{children}</QueryClientProvider>);
}

const APPROVAL: ApprovalRead = {
  id: "ap1",
  task_id: "t1",
  requested_action: "browser_submit",
  params: { effect: "refund.create", amount_paise: 3500000 },
  params_hash: "h",
  reason: "large refund needs a human",
  policy_rule_id: "P-REF-004",
  status: "pending",
  approver: null,
  resolved_at: null,
  expires_at: null,
  created_at: "2026-10-05T00:00:00.000Z",
};

describe("ApprovalQueueView", () => {
  it("approves with the named approver and reports the requeue", async () => {
    post.mockResolvedValueOnce({ data: { ...APPROVAL, status: "approved" } });
    providers(<ApprovalQueueView approvals={[APPROVAL]} />);

    expect(screen.getByText(/large refund needs a human/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Approver"), { target: { value: "duty-ops" } });
    fireEvent.click(screen.getByRole("button", { name: "Approve" }));

    await waitFor(() =>
      expect(post).toHaveBeenCalledWith("/api/approvals/ap1/approve", { approver: "duty-ops" }),
    );
    expect(await screen.findByText(/Decision recorded/)).toBeInTheDocument();
  });

  it("rejects through the reject endpoint", async () => {
    post.mockResolvedValueOnce({ data: { ...APPROVAL, status: "rejected" } });
    providers(<ApprovalQueueView approvals={[APPROVAL]} />);
    fireEvent.click(screen.getByRole("button", { name: "Reject" }));
    await waitFor(() =>
      expect(post).toHaveBeenCalledWith("/api/approvals/ap1/reject", { approver: "duty-ops" }),
    );
  });

  it("renders the empty queue state", () => {
    providers(<ApprovalQueueView approvals={[]} />);
    expect(screen.getByText("No approvals waiting.")).toBeInTheDocument();
  });
});

const CLARIFICATION: ClarificationRead = {
  id: "c1",
  task_id: "t1",
  kind: "operator",
  question: "Which customer?",
  answer: null,
  answered_by: null,
  status: "pending",
  created_at: "2026-10-05T00:00:00.000Z",
};

describe("ClarificationQueueView", () => {
  it("answers the question and reports the requeue", async () => {
    post.mockResolvedValueOnce({ data: { ...CLARIFICATION, status: "answered" } });
    providers(<ClarificationQueueView clarifications={[CLARIFICATION]} />);

    fireEvent.change(screen.getByLabelText("Answer"), { target: { value: "Asha (C101)" } });
    fireEvent.click(screen.getByRole("button", { name: "Answer" }));

    await waitFor(() =>
      expect(post).toHaveBeenCalledWith("/api/clarifications/c1/answer", {
        answer: "Asha (C101)",
        answered_by: "duty-ops",
      }),
    );
    expect(await screen.findByText(/Answer recorded/)).toBeInTheDocument();
  });
});
