import type { ChatAction } from "@/services/chat-api";

export type SupportChatMessage = {
  id: string;
  from: "you" | "bot";
  text: string;
  ts: string;
  taskId?: string | null;
  actions?: ChatAction[];
};

export type SupportChatSession = {
  id: string;
  title: string;
  updatedAt: string;
  activeTaskId: string | null;
  activeTicketId: string | null;
  messages: SupportChatMessage[];
};

const KEY = "ns-support-chat-sessions-v1";
const MAX_SESSIONS = 30;

function uid(prefix: string): string {
  return `${prefix}-${Date.now().toString(36)}-${Math.floor(Math.random() * 1e6).toString(36)}`;
}

export function newSupportSession(): SupportChatSession {
  return {
    id: uid("chat"),
    title: "New conversation",
    updatedAt: new Date().toISOString(),
    activeTaskId: null,
    activeTicketId: null,
    messages: [],
  };
}

export function titleForSupport(messages: SupportChatMessage[]): string {
  const first = messages.find((m) => m.from === "you");
  if (!first) return "New conversation";
  const text = first.text.replace(/\s+/g, " ").trim();
  return text.length > 42 ? `${text.slice(0, 42)}…` : text;
}

export function loadSupportSessions(): SupportChatSession[] {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as SupportChatSession[];
    return Array.isArray(parsed) ? parsed.slice(0, MAX_SESSIONS) : [];
  } catch {
    return [];
  }
}

export function saveSupportSession(session: SupportChatSession): SupportChatSession[] {
  const rest = loadSupportSessions().filter((e) => e.id !== session.id);
  const next = [session, ...rest].slice(0, MAX_SESSIONS);
  try {
    localStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    // Private mode / quota: history is best-effort, chat still works.
  }
  return next;
}

export function deleteSupportSession(id: string): SupportChatSession[] {
  const next = loadSupportSessions().filter((e) => e.id !== id);
  try {
    localStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    // Best-effort (see saveSupportSession).
  }
  return next;
}
