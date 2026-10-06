import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { TaskChatView, eventsToMessages } from "@/features/worker/chat/components/TaskChat";
import { axiosClient } from "@/shared/api/axiosClient";
import type {
  ApprovalRead,
  AuditEventRead,
  ClarificationRead,
  TaskRead,
} from "@/features/worker/types";

vi.mock("@/shared/api/axiosClient", () => ({
  axiosClient: { get: vi.fn(), post: vi.fn() },
}));

const get = axiosClient.get as unknown as ReturnType<typeof vi.fn>;
const post = axiosClient.post as unknown as ReturnType<typeof vi.fn>;

function providers(children: React.ReactNode) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>,
  );
}

function ev(seq: number, kind: string, extra: Partial<AuditEventRead> = {}): AuditEventRead {
  return {
    id: `e${seq}`,
    task_id: "t1",
    run_id: "r1",
    seq,
    ts: "2026-10-05T00:00:00.000Z",
    node: null,
    tool: null,
    kind,
    status: null,
    error_type: null,
    retry_count: 0,
    duration_ms: null,
    policy_result: null,
    verification_result: null,
    payload: {},
    ...extra,
  };
}

const TASK: TaskRead = {
  id: "t1",
  text: "Replace the cable (ORD-1950).",
  mode: "explicit",
  status: "running",
  current_state: "running",
  scenario_ref: null,
  created_by: "api",
  created_at: "2026-10-05T00:00:00.000Z",
};

const APPROVAL: ApprovalRead = {
  id: "ap1",
  task_id: "t1",
  requested_action: "browser_submit",
  params: {},
  params_hash: "h",
  reason: "needs a human",
  policy_rule_id: "P-REF-003",
  status: "pending",
  approver: null,
  resolved_at: null,
  expires_at: null,
  created_at: "2026-10-05T00:00:00.000Z",
};

const CLARIFICATION: ClarificationRead = {
  id: "c1",
  task_id: "t1",
  kind: "operator",
  question: "Replace or refund?",
  answer: null,
  answered_by: null,
  status: "pending",
  created_at: "2026-10-05T00:00:00.000Z",
};

describe("eventsToMessages", () => {
  it("narrates lifecycle, policy, tools and failures, skipping noise", () => {
    const messages = eventsToMessages([
      ev(1, "run.start", { payload: { attempt: 2 } }),
      ev(2, "node.transition", { node: "decide" }),
      ev(3, "contract.compiled", { payload: { effects: 1, ambiguity: [] } }),
      ev(4, "policy.decision", {
        policy_result: "ALLOW",
        payload: { rule_id: "P-REPL-001", reason: "small replacement" },
      }),
      ev(5, "tool.call", { tool: "browser_submit" }),
      ev(6, "failure.classified", { error_type: "timeout" }),
      ev(7, "approval.park"),
      ev(8, "verification.result", { verification_result: "VERIFIED" }),
      ev(9, "run.end", { payload: { status: "succeeded" } }),
    ]);
    const texts = messages.map((message) => message.text);
    expect(texts).toEqual([
      "Run started — attempt 2.",
      "Contract compiled — 1 effect locked.",
      "Policy ALLOW — P-REPL-001: small replacement",
      "Committing via the Ops UI…",
      "Something failed (timeout). Working out recovery…",
      "This step needs a human decision — the run is parked. Decide below.",
      "Verifier says: VERIFIED.",
      "Done — verified effects committed.",
    ]);
  });
});

describe("TaskChatView", () => {
  beforeEach(() => {
    get.mockResolvedValue({ data: [] });
    post.mockClear();
    get.mockClear();
  });

  it("routes the reply to an open clarification", async () => {
    post.mockResolvedValueOnce({ data: { ...CLARIFICATION, status: "answered" } });
    providers(<TaskChatView task={TASK} events={[]} approvals={[]} clarifications={[CLARIFICATION]} />);

    expect(screen.getByText("Replace the cable (ORD-1950).")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Reply"), { target: { value: "Replace it" } });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() =>
      expect(post).toHaveBeenCalledWith("/api/clarifications/c1/answer", {
        answer: "Replace it",
        answered_by: "duty-ops",
      }),
    );
  });

  it("decides approvals with explicit buttons, never chat text", async () => {
    post.mockResolvedValueOnce({ data: { ...APPROVAL, status: "approved" } });
    providers(<TaskChatView task={TASK} events={[]} approvals={[APPROVAL]} clarifications={[]} />);

    fireEvent.click(screen.getByRole("button", { name: "Approve" }));
    await waitFor(() =>
      expect(post).toHaveBeenCalledWith("/api/approvals/ap1/approve", { approver: "duty-ops" }),
    );
    expect(await screen.findByText(/Decision recorded/)).toBeInTheDocument();
  });

  it("starts a follow-up task when nothing is open", async () => {
    post.mockResolvedValueOnce({ data: { ...TASK, id: "t2" } });
    providers(<TaskChatView task={TASK} events={[]} approvals={[]} clarifications={[]} />);

    fireEvent.change(screen.getByLabelText("Reply"), { target: { value: "Now reply to it" } });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() =>
      expect(post).toHaveBeenCalledWith("/api/tasks", {
        text: "Now reply to it",
        mode: "explicit",
      }),
    );
    expect(await screen.findByText(/Follow-up started/)).toBeInTheDocument();
  });
});
