import type { AssistantAction } from "./assistantApi";

export type StoredMessage = {
  id: string;
  from: "you" | "bot";
  text: string;
  ts: string;
  taskId?: string | null;
  actions?: AssistantAction[];
};

export type ChatSession = {
  id: string;
  title: string;
  updatedAt: string;
  activeTaskId: string | null;
  messages: StoredMessage[];
};

const KEY = "ns-chat-sessions-v1";
const MAX_SESSIONS = 30;

function uid(prefix: string) {
  return `${prefix}-${Date.now().toString(36)}-${Math.floor(Math.random() * 1e6).toString(36)}`;
}

export function newSession(): ChatSession {
  return {
    id: uid("chat"),
    title: "New conversation",
    updatedAt: new Date().toISOString(),
    activeTaskId: null,
    messages: [],
  };
}

/** Title from the first user turn (kept short for the history rail). */
export function titleFor(messages: StoredMessage[]): string {
  const first = messages.find((message) => message.from === "you");
  if (!first) return "New conversation";
  const text = first.text.replace(/\s+/g, " ").trim();
  return text.length > 42 ? `${text.slice(0, 42)}…` : text;
}

export function loadSessions(): ChatSession[] {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as ChatSession[];
    return Array.isArray(parsed) ? parsed.slice(0, MAX_SESSIONS) : [];
  } catch {
    return [];
  }
}

export function saveSession(session: ChatSession): ChatSession[] {
  const rest = loadSessions().filter((entry) => entry.id !== session.id);
  const next = [session, ...rest].slice(0, MAX_SESSIONS);
  try {
    localStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    // Private mode / quota: history is best-effort, chat still works.
  }
  return next;
}

export function deleteSession(id: string): ChatSession[] {
  const next = loadSessions().filter((entry) => entry.id !== id);
  try {
    localStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    // Best-effort (see saveSession).
  }
  return next;
}
