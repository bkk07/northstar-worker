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
