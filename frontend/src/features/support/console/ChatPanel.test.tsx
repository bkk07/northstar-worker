import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import type { AssistantMessage } from "@/features/worker/assistant/useAssistant";
import { ChatPanel } from "./ChatPanel";

const BOT_WITH_APPROVAL: AssistantMessage = {
  id: "bot-1",
  from: "bot",
  text: "Task abc12345 is waiting for approval.",
  ts: "2026-10-05T00:00:00.000Z",
  actions: [
    {
      kind: "approval",
      label: "Approve (abc12345)",
      task_id: "abc12345-0000-0000-0000-000000000000",
      approval_id: "appr-1",
      decision: "approve",
    },
    {
      kind: "approval",
      label: "Reject (abc12345)",
      task_id: "abc12345-0000-0000-0000-000000000000",
      approval_id: "appr-1",
      decision: "reject",
    },
  ],
};

function panel(overrides: Partial<Parameters<typeof ChatPanel>[0]> = {}) {
  const props: Parameters<typeof ChatPanel>[0] = {
    messages: [BOT_WITH_APPROVAL],
    narration: [],
    taskStatus: "waiting_for_approval",
    activeTaskId: "abc12345-0000-0000-0000-000000000000",
    busy: false,
    error: null,
    deciding: null,
    onRetry: vi.fn(),
    onSend: vi.fn(),
    onDecide: vi.fn(),
    ...overrides,
  };
  render(
    <MemoryRouter>
      <ChatPanel {...props} />
    </MemoryRouter>,
  );
  return props;
}

describe("ChatPanel", () => {
  it("renders inline approve/reject buttons bound to the approval", () => {
    panel();
    expect(screen.getByRole("button", { name: "Approve (abc12345)" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reject (abc12345)" })).toBeInTheDocument();
  });

  it("decides through the callback, never through typed text", () => {
    const props = panel();
    fireEvent.click(screen.getByRole("button", { name: "Approve (abc12345)" }));
    expect(props.onDecide).toHaveBeenCalledWith("appr-1", "approve");
    // Decided groups hide so a stray click can never double-decide.
    expect(
      screen.queryByRole("button", { name: "Approve (abc12345)" }),
    ).not.toBeInTheDocument();
  });

  it("shows the new Q&A suggestion chips on a fresh thread", () => {
    panel({
      messages: [
        { id: "g", from: "bot", text: "Hi", ts: "2026-10-05T00:00:00.000Z" },
      ],
    });
    expect(
      screen.getByRole("button", { name: "Anything waiting for approval?" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "What's the refund policy?" }),
    ).toBeInTheDocument();
  });

  it("sends composer text and clears the input", () => {
    const props = panel();
    fireEvent.change(screen.getByLabelText("Message the bot"), {
      target: { value: "tell me about TCK-102" },
    });
    fireEvent.submit(screen.getByLabelText("Chat with the bot"));
    expect(props.onSend).toHaveBeenCalledWith("tell me about TCK-102");
    expect(screen.getByLabelText("Message the bot")).toHaveValue("");
  });
});
