import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { getErrorMessage } from "@/shared/lib/errors";
import { postChat, type AssistantAction } from "./assistantApi";

export type AssistantMessage = {
  id: string;
  from: "you" | "bot";
  text: string;
  ts: string;
  taskId?: string | null;
  actions?: AssistantAction[];
};

const GREETING: AssistantMessage = {
  id: "greeting",
  from: "bot",
  text: "Hi — I'm the support bot. Tell me “solve ticket TCK-…” and I'll run it, narrating here. I ask when I need you, and approvals always use the buttons on the task page.",
  ts: new Date().toISOString(),
};

let counter = 0;
function nextId(prefix: string) {
  counter += 1;
  return `${prefix}-${Date.now()}-${counter}`;
}

/**
 * Chat thread state: local messages plus one `postChat` mutation per turn.
 * The backend reply may bind the thread to a task; the page narrates that
 * task's journal underneath. Thread state resets only on unmount.
 */
export function useAssistant() {
  const [messages, setMessages] = useState<AssistantMessage[]>([GREETING]);
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);

  const sendState = useMutation({
    mutationFn: (text: string) => postChat(text),
    onSuccess: (reply, text) => {
      setMessages((previous) => [
        ...previous.filter((message) => message.id !== "pending-you"),
        {
          id: nextId("you"),
          from: "you",
          text,
          ts: new Date().toISOString(),
        },
        {
          id: nextId("bot"),
          from: "bot",
          text: reply.reply,
          ts: new Date().toISOString(),
          taskId: reply.task_id,
          actions: reply.actions,
        },
      ]);
      if (reply.task_id) setActiveTaskId(reply.task_id);
    },
    onError: () => {
      setMessages((previous) => previous.filter((message) => message.id !== "pending-you"));
    },
  });

  function send(text: string) {
    const trimmed = text.trim();
    if (!trimmed || sendState.isPending) return;
    setMessages((previous) => [
      ...previous,
      { id: "pending-you", from: "you", text: trimmed, ts: new Date().toISOString() },
    ]);
    sendState.mutate(trimmed);
  }

  return {
    messages,
    send,
    busy: sendState.isPending,
    error: sendState.isError ? getErrorMessage(sendState.error) : null,
    retry: () => sendState.reset(),
    activeTaskId,
  };
}
