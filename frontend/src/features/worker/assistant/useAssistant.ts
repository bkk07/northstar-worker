import { useMutation } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { getErrorMessage } from "@/shared/lib/errors";
import { postChat, type AssistantAction } from "./assistantApi";
import {
  deleteSession,
  loadSessions,
  newSession,
  saveSession,
  titleFor,
  type ChatSession,
  type StoredMessage,
} from "./chatHistory";

export type AssistantMessage = StoredMessage;

export type { AssistantAction };

const GREETING_TEXT =
  "Hi — I'm the support bot. Ask me anything about tickets, orders, products, and policies, or tell me “solve ticket TCK-…” and I'll run it, narrating here. Approvals always use the buttons — typed “yes” never counts.";

function greeting(): AssistantMessage {
  return { id: "greeting", from: "bot", text: GREETING_TEXT, ts: new Date().toISOString() };
}

let counter = 0;
function nextId(prefix: string) {
  counter += 1;
  return `${prefix}-${Date.now()}-${counter}`;
}

/**
 * Chat thread state with ChatGPT-style sessions (localStorage history).
 * One `postChat` mutation per turn; the backend reply may bind the thread
 * to a task, which the page narrates underneath. Switching sessions swaps
 * the message list and the bound task; everything persists locally.
 */
export function useAssistant(initialSessionId?: string | null) {
  const [sessions, setSessions] = useState<ChatSession[]>(() => loadSessions());
  const [activeId, setActiveId] = useState<string | null>(initialSessionId ?? null);
  const [messages, setMessages] = useState<AssistantMessage[]>(() => {
    const found = initialSessionId
      ? (loadSessions().find((s) => s.id === initialSessionId) ?? null)
      : null;
    return found && found.messages.length > 0 ? found.messages : [greeting()];
  });
  const [activeTaskId, setActiveTaskId] = useState<string | null>(() => {
    const found = initialSessionId
      ? (loadSessions().find((s) => s.id === initialSessionId) ?? null)
      : null;
    return found?.activeTaskId ?? null;
  });

  // Persist every turn (title follows the first user message).
  useEffect(() => {
    if (messages.length <= 1 && !activeTaskId) return;
    const session: ChatSession = {
      id: activeId ?? newSession().id,
      title: titleFor(messages),
      updatedAt: new Date().toISOString(),
      activeTaskId,
      messages,
    };
    setSessions(saveSession(session));
    if (!activeId) setActiveId(session.id);
  }, [messages, activeTaskId]);

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
      { id: nextId("pending-you"), from: "you", text: trimmed, ts: new Date().toISOString() },
    ]);
    sendState.mutate(trimmed);
  }

  function appendBot(text: string) {
    setMessages((previous) => [
      ...previous,
      { id: nextId("bot"), from: "bot", text, ts: new Date().toISOString() },
    ]);
  }

  function newChat() {
    setActiveId(null);
    setMessages([greeting()]);
    setActiveTaskId(null);
  }

  function switchSession(id: string) {
    const found = sessions.find((session) => session.id === id);
    if (!found) return;
    setActiveId(found.id);
    setMessages(found.messages.length > 0 ? found.messages : [greeting()]);
    setActiveTaskId(found.activeTaskId);
  }

  function removeSession(id: string) {
    setSessions(deleteSession(id));
    if (activeId === id) newChat();
  }

  return {
    messages,
    send,
    appendBot,
    newChat,
    switchSession,
    removeSession,
    sessions,
    activeSessionId: activeId,
    busy: sendState.isPending,
    error: sendState.isError ? getErrorMessage(sendState.error) : null,
    retry: () => sendState.reset(),
    activeTaskId,
  };
}
