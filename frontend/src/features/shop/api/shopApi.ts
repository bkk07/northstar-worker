import { axiosClient } from "@/shared/api/axiosClient";
import type { CustomerRead, OrderRead, ShopTicketCreate, TicketRead } from "../types";

// Axios calls only; server state lives in hooks (TanStack Query).
export async function listOrders(customerCode?: string): Promise<OrderRead[]> {
  const { data } = await axiosClient.get<OrderRead[]>("/api/shop/orders", {
    params: customerCode ? { customer_code: customerCode } : {},
  });
  return data;
}

export async function getOrder(orderCode: string): Promise<OrderRead> {
  const { data } = await axiosClient.get<OrderRead>(`/api/shop/orders/${orderCode}`);
  return data;
}

export async function createTicket(payload: ShopTicketCreate): Promise<TicketRead> {
  const { data } = await axiosClient.post<TicketRead>("/api/shop/tickets", payload);
  return data;
}

export async function getTicket(ticketCode: string): Promise<TicketRead> {
  const { data } = await axiosClient.get<TicketRead>(`/api/shop/tickets/${ticketCode}`);
  return data;
}

export async function listOrderTickets(orderCode: string): Promise<TicketRead[]> {
  const { data } = await axiosClient.get<TicketRead[]>(
    `/api/shop/orders/${orderCode}/tickets`,
  );
  return data;
}

export async function getCustomer(customerId: string): Promise<CustomerRead> {
  const { data } = await axiosClient.get<CustomerRead>(`/api/read/customers/${customerId}`);
  return data;
}
