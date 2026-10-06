import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { AssistantView } from "@/features/worker/pages/WorkerAssistantPage";
import type { AssistantMessage } from "@/features/worker/assistant/useAssistant";
import type { ChatMessage } from "@/features/worker/chat/components/TaskChat";

const BOT: AssistantMessage = {
  id: "bot-1",
  from: "bot",
  text: "Hi — I'm the support bot.",
  ts: "2026-10-05T00:00:00.000Z",
};

function view(overrides: Partial<Parameters<typeof AssistantView>[0]> = {}) {
  const props: Parameters<typeof AssistantView>[0] = {
    messages: [BOT],
    narration: [],
    taskStatus: undefined,
    activeTaskId: null,
    busy: false,
    error: null,
    onRetry: vi.fn(),
    onSend: vi.fn(),
    ...overrides,
  };
  render(
    <MemoryRouter>
      <AssistantView {...props} />
    </MemoryRouter>,
  );
  return props;
}

describe("AssistantView", () => {
  it("greets with suggestion chips on a fresh thread", () => {
    view();
    expect(screen.getByText(/I'm the support bot/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Show open tickets" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "What can you do?" })).toBeInTheDocument();
  });

  it("sends the composer text and clears the input", () => {
    const props = view();
    fireEvent.change(screen.getByLabelText("Message the bot"), {
      target: { value: "solve ticket TCK-ABC123" },
    });
    fireEvent.submit(screen.getByLabelText("Chat with the bot"));
    expect(props.onSend).toHaveBeenCalledWith("solve ticket TCK-ABC123");
    expect(screen.getByLabelText("Message the bot")).toHaveValue("");
  });

  it("sends a suggestion chip on click", () => {
    const props = view();
    fireEvent.click(screen.getByRole("button", { name: "Show open tickets" }));
    expect(props.onSend).toHaveBeenCalledWith("Show open tickets");
  });

  it("renders user and bot bubbles plus action links", () => {
    view({
      messages: [
        BOT,
        {
          id: "you-1",
          from: "you",
          text: "solve ticket TCK-ABC123",
          ts: "2026-10-05T00:01:00.000Z",
        },
        {
          id: "bot-2",
          from: "bot",
          text: "On it — solving TCK-ABC123.",
          ts: "2026-10-05T00:01:01.000Z",
          taskId: "task-1",
          actions: [{ kind: "task", label: "Open task abcd1234", href: "/worker/tasks/task-1" }],
        },
      ],
    });
    expect(screen.getByText("solve ticket TCK-ABC123")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open task abcd1234" })).toHaveAttribute(
      "href",
      "/worker/tasks/task-1",
    );
  });

  it("narrates the bound run and nudges decisions to the task page", () => {
    const narration: ChatMessage[] = [
      { key: "e1", from: "worker", text: "Run started — attempt 1.", ts: "2026-10-05T00:02:00Z" },
      { key: "e2", from: "worker", text: "Contract compiled — 1 effect locked.", ts: "2026-10-05T00:02:01Z" },
    ];
    view({
      narration,
      taskStatus: "waiting_for_approval",
      activeTaskId: "task-1",
    });
    expect(screen.getByText("Run started — attempt 1.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "open the task to decide" })).toHaveAttribute(
      "href",
      "/worker/tasks/task-1",
    );
  });

  it("shows the typing indicator while busy", () => {
    view({ busy: true });
    expect(screen.getByLabelText("Bot is typing")).toBeInTheDocument();
  });

  it("shows send errors with a dismiss action", () => {
    const props = view({ error: "Network error" });
    expect(screen.getByRole("alert")).toHaveTextContent("Network error");
    fireEvent.click(screen.getByRole("button", { name: "Dismiss" }));
    expect(props.onRetry).toHaveBeenCalled();
  });
});
