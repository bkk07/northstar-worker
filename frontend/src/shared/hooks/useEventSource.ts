import { useEffect, useRef, useState } from "react";

// Typed EventSource hook for the worker live timeline (Phase 25).
// Auth travels in the session cookie (same-origin relative URL) —
// EventSource sends no headers, so no token ever enters the URL or bundle.
export type SseStatus = "connecting" | "open" | "closed" | "error";

export type TaskAuditEvent = {
  id: string;
  task_id: string;
  run_id: string | null;
  seq: number;
  ts: string;
  node: string | null;
  tool: string | null;
  kind: string;
  status: string | null;
  error_type: string | null;
  retry_count: number;
  duration_ms: number | null;
  policy_result: string | null;
  verification_result: string | null;
  payload: Record<string, unknown>;
};

export function useEventSource<T>(url: string | null, eventName = "audit") {
  const [events, setEvents] = useState<T[]>([]);
  const [status, setStatus] = useState<SseStatus>("closed");
  const [lastEventId, setLastEventId] = useState("");
  const sourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (url === null) {
      return;
    }
    setStatus("connecting");
    const source = new EventSource(url);
    sourceRef.current = source;
    source.onopen = () => setStatus("open");
    source.onerror = () => setStatus("error");
    const onEvent = (message: MessageEvent<string>) => {
      setLastEventId(message.lastEventId);
      try {
        setEvents((previous) => [...previous, JSON.parse(message.data) as T]);
      } catch {
        // Malformed frames never corrupt the timeline; the next id resumes.
      }
    };
    source.addEventListener(eventName, onEvent as EventListener);
    return () => {
      source.removeEventListener(eventName, onEvent as EventListener);
      source.close();
      sourceRef.current = null;
      setStatus("closed");
    };
  }, [url, eventName]);

  return { events, status, lastEventId };
}
