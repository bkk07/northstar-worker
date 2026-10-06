import { api } from "@/lib/api-client";
import type { Ticket, TicketDetail, TicketMessage } from "@/types";

export type RaiseTicketInput = {
  subject: string;
  category: string;
  description: string;
  order_id?: string | null;
  priority?: string;
};

export async function listTickets(): Promise<Ticket[]> {
  const { data } = await api.get<Ticket[]>("/tickets");
  return data;
}

export async function getTicket(id: string): Promise<TicketDetail> {
  const { data } = await api.get<TicketDetail>(`/tickets/${id}`);
  return data;
}

export async function raiseTicket(input: RaiseTicketInput): Promise<TicketDetail> {
  const { data } = await api.post<TicketDetail>("/tickets", {
    subject: input.subject,
    category: input.category,
    description: input.description,
    order_id: input.order_id ?? null,
    priority: input.priority ?? "NORMAL",
  });
  return data;
}

export async function replyToTicket(id: string, message: string): Promise<TicketMessage> {
  const { data } = await api.post<TicketMessage>(`/tickets/${id}/messages`, { message });
  return data;
}
