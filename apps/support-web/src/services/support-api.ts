import { api } from "@/lib/api-client";

export type DashboardStats = {
  by_status: Record<string, number>;
  summary: { open: number; in_progress: number; waiting: number; resolved: number };
};

export type QueueTicket = {
  id: string;
  ticket_number: string;
  subject: string;
  category: string;
  priority: string;
  status: string;
  customer_name: string;
  customer_email: string;
  order_number: string | null;
  message_count: number;
  created_at: string;
};

export type ConsoleMessage = {
  id: string;
  sender_type: string;
  message: string;
  is_internal: boolean;
  created_at: string;
};

export type ConsoleTicketDetail = {
  id: string;
  ticket_number: string;
  subject: string;
  description: string;
  category: string;
  priority: string;
  status: string;
  resolution: string | null;
  created_at: string;
  customer: { id: string; name: string; email: string; created_at: string | null };
  related_order: {
    id: string;
    order_number: string;
    status: string;
    total_display: string;
    payment_status: string;
    payment_reference: string | null;
    shipping_address: string;
    ordered_at: string;
    items: { product_name: string; quantity: number; unit_price_paise: number; line_total_paise: number }[];
  } | null;
  policies: { product_name: string; summary: string; return_allowed: boolean; refund_allowed: boolean; cancellation_allowed: boolean }[];
  recent_orders: { id: string; order_number: string; status: string; total_display: string; ordered_at: string }[];
  previous_tickets: { id: string; ticket_number: string; subject: string; status: string }[];
  messages: ConsoleMessage[];
};

export async function fetchStats(): Promise<DashboardStats> {
  const { data } = await api.get<DashboardStats>("/support/stats");
  return data;
}

export type QueueQuery = { status?: string; priority?: string; q?: string };

export async function fetchQueue(query: QueueQuery = {}): Promise<QueueTicket[]> {
  const { data } = await api.get<QueueTicket[]>("/support/tickets", { params: query });
  return data;
}

export async function fetchTicketDetail(id: string): Promise<ConsoleTicketDetail> {
  const { data } = await api.get<ConsoleTicketDetail>(`/support/tickets/${id}`);
  return data;
}

export async function replyToTicket(id: string, message: string): Promise<ConsoleMessage> {
  const { data } = await api.post<ConsoleMessage>(`/support/tickets/${id}/reply`, { message });
  return data;
}

export async function addInternalNote(id: string, message: string): Promise<ConsoleMessage> {
  const { data } = await api.post<ConsoleMessage>(`/support/tickets/${id}/notes`, { message });
  return data;
}

export async function resolveTicket(id: string, resolution: string): Promise<{ id: string; status: string }> {
  const { data } = await api.post(`/support/tickets/${id}/resolve`, { resolution });
  return data;
}

export async function escalateTicket(id: string, reason?: string): Promise<{ id: string; status: string }> {
  const { data } = await api.post(`/support/tickets/${id}/escalate`, { reason: reason ?? null });
  return data;
}

export type SolveResponse = {
  run_id: string;
  status: string;
  intent: string | null;
  decision: string | null;
  approval_id: string | null;
};

export type TraceStep = {
  key: string;
  label: string;
  state: string;
  at: string | null;
  detail?: string | null;
};

export type AuditEvent = { event: string; actor: string; at: string };

export type TraceApproval = {
  id: string;
  ticket_id: string;
  ticket_number: string;
  action_type: string;
  action_payload: Record<string, unknown>;
  status: string;
  requested_at: string;
  resolved_at: string | null;
  human_note: string | null;
  expires_at: string | null;
};

export type TicketTrace = {
  ticket_id: string;
  ticket_status: string;
  run: { id: string; status: string; intent: string | null; workflow: string | null; decision: string | null } | null;
  steps: TraceStep[];
  approvals: TraceApproval[];
  audits: AuditEvent[];
};

export async function solveTicket(id: string): Promise<SolveResponse> {
  const { data } = await api.post<SolveResponse>(`/support/tickets/${id}/solve`);
  return data;
}

export async function fetchTrace(id: string): Promise<TicketTrace> {
  const { data } = await api.get<TicketTrace>(`/support/tickets/${id}/trace`);
  return data;
}

export async function fetchApprovals(status = "PENDING"): Promise<TraceApproval[]> {
  const { data } = await api.get<TraceApproval[]>("/support/approvals", { params: { status } });
  return data;
}

export async function decideApproval(
  id: string,
  approved: boolean,
  note?: string,
): Promise<{ approval_id: string; status: string; executed: boolean }> {
  const { data } = await api.post(`/support/approvals/${id}/decision`, {
    approved,
    note: note ?? null,
  });
  return data;
}

export async function takeOverTicket(id: string): Promise<{ cancelled: boolean }> {
  const { data } = await api.post(`/support/tickets/${id}/takeover`);
  return data;
}

export function subscribeActivity(
  id: string,
  onEvent: (type: string) => void,
  onError?: () => void,
): () => void {
  const base = (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000";
  const token = localStorage.getItem("ns_support_token");
  // EventSource cannot set headers; the backend also accepts the staff
  // token via query for this stream only (prototype scope).
  const source = new EventSource(
    `${base}/support/tickets/${id}/activity${token ? `?token=${encodeURIComponent(token)}` : ""}`,
  );
  const handler = (e: Event) => {
    onEvent((e as MessageEvent).type || "message");
  };
  source.addEventListener("ai_started", handler);
  source.addEventListener("ai_activity", handler);
  source.addEventListener("intent_classified", handler);
  source.addEventListener("tool_started", handler);
  source.addEventListener("tool_done", handler);
  source.addEventListener("tool_failed", handler);
  source.addEventListener("waiting_for_approval", handler);
  source.addEventListener("approval_required", handler);
  source.addEventListener("approval_approved", handler);
  source.addEventListener("approval_rejected", handler);
  source.addEventListener("approval_expired", handler);
  source.addEventListener("ticket_resolved", handler);
  source.addEventListener("run_completed", handler);
  source.addEventListener("run_escalated", handler);
  source.addEventListener("waiting_for_customer", handler);
  source.onerror = () => {
    source.close();
    onError?.();
  };
  return () => source.close();
}
