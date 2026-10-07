import { useMutation } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { staffApiErrorMessage } from "@/lib/api-client";
import {
  deleteSupportSession,
  loadSupportSessions,
  newSupportSession,
  saveSupportSession,
  titleForSupport,
  type SupportChatMessage,
  type SupportChatSession,
} from "@/lib/chat-history";
import { postSupportChat } from "@/services/chat-api";

const GREETING_TEXT =
  "Hi — I'm the support AI. Talk to me directly here. Tell me “solve ticket TCK-…” with any extra context and I'll run it, or ask about tickets, orders, products, and policies. Approvals always use the buttons — typed “yes” never counts.";

/** Single in-flight optimistic bubble id (the isPending guard allows only one). */
const PENDING_ID = "pending-you";

function isGhost(m: SupportChatMessage): boolean {
  return m.id === PENDING_ID || m.id.startsWith(`${PENDING_ID}-`);
}

function greeting(): SupportChatMessage {
  return { id: "greeting", from: "bot", text: GREETING_TEXT, ts: new Date().toISOString() };
}

let counter = 0;
function nextId(prefix: string): string {
  counter += 1;
  return `${prefix}-${Date.now()}-${counter}`;
}

/**
 * Chat thread state for the support console (/chat).
 * Mirrors the worker assistant thread but scoped to the support app
 * (own localStorage key, own staff authed client). One postSupportChat
 * mutation per turn; the reply may bind the thread to a worker task.
 */
export function useSupportChat(initialSessionId?: string | null) {
  const [sessions, setSessions] = useState<SupportChatSession[]>(() => loadSupportSessions());
  const [activeId, setActiveId] = useState<string | null>(initialSessionId ?? null);
  const [messages, setMessages] = useState<SupportChatMessage[]>(() => {
    const found = initialSessionId
      ? loadSupportSessions().find((s) => s.id === initialSessionId) ?? null
      : null;
    const clean = (found?.messages ?? []).filter((m) => !isGhost(m));
    return clean.length > 0 ? clean : [greeting()];
  });
  const [activeTaskId, setActiveTaskId] = useState<string | null>(() => {
    const found = initialSessionId
      ? loadSupportSessions().find((s) => s.id === initialSessionId) ?? null
      : null;
    return found?.activeTaskId ?? null;
  });
  // Ticket the thread is grounded on (canonical runs act on this ticket).
  const [activeTicketId, setActiveTicketId] = useState<string | null>(() => {
    const found = initialSessionId
      ? loadSupportSessions().find((s) => s.id === initialSessionId) ?? null
      : null;
    return found?.activeTicketId ?? null;
  });

  useEffect(() => {
    if (messages.length <= 1 && !activeTaskId && !activeTicketId) return;
    const session: SupportChatSession = {
      id: activeId ?? newSupportSession().id,
      title: titleForSupport(messages),
      updatedAt: new Date().toISOString(),
      activeTaskId,
      activeTicketId,
      // Never persist the optimistic bubble: a refresh mid-flight must not
      // resurrect a ghost "you" message with no reply.
      messages: messages.filter((m) => !isGhost(m)),
    };
    setSessions(saveSupportSession(session));
    if (!activeId) setActiveId(session.id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [messages, activeTaskId, activeTicketId]);

  const sendState = useMutation({
    mutationFn: (vars: { text: string; history: string[] }) =>
      postSupportChat(vars.text, vars.history),
    onSuccess: (reply, vars) => {
      const text = vars.text;
      setMessages((prev) => [
        ...prev.filter((m) => !isGhost(m)),
        { id: nextId("you"), from: "you", text, ts: new Date().toISOString() },
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
      if (reply.ticket_id) setActiveTicketId(reply.ticket_id);
    },
    onError: () => {
      setMessages((prev) => prev.filter((m) => !isGhost(m)));
    },
  });

  function send(text: string) {
    const trimmed = text.trim();
    if (!trimmed || sendState.isPending) return;
    // Thread context (excluding the greeting) so the backend can resolve
    // follow-ups like "yes, look at that ticket" against earlier codes.
    const history = messages
      .filter((m) => m.id !== "greeting" && !isGhost(m))
      .slice(-6)
      .map((m) => m.text);
    setMessages((prev) => [
      ...prev.filter((m) => !isGhost(m)),
      { id: PENDING_ID, from: "you", text: trimmed, ts: new Date().toISOString() },
    ]);
    sendState.mutate({ text: trimmed, history });
  }

  function appendBot(text: string) {
    setMessages((prev) => [
      ...prev,
      { id: nextId("bot"), from: "bot", text, ts: new Date().toISOString() },
    ]);
  }

  function newChat() {
    setActiveId(null);
    setMessages([greeting()]);
    setActiveTaskId(null);
    setActiveTicketId(null);
  }

  function switchSession(id: string) {
    const found = sessions.find((s) => s.id === id) ?? loadSupportSessions().find((s) => s.id === id);
    if (!found) return;
    setActiveId(found.id);
    const clean = found.messages.filter((m) => !isGhost(m));
    setMessages(clean.length > 0 ? clean : [greeting()]);
    setActiveTaskId(found.activeTaskId);
    setActiveTicketId(found.activeTicketId ?? null);
  }

  function removeSession(id: string) {
    setSessions(deleteSupportSession(id));
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
    error: sendState.isError ? staffApiErrorMessage(sendState.error, "The AI support run could not be completed. No customer action was confirmed. Please retry or take over the ticket.") : null,
    retry: () => sendState.reset(),
    activeTaskId,
    activeTicketId,
  };
}
