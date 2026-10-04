import { axiosClient } from "@/shared/api/axiosClient";
import type { TicketListResponse, TicketRead, UiFlags } from "../../types";

export async function listTickets(page: number, pageSize = 10): Promise<TicketListResponse> {
  const { data } = await axiosClient.get<TicketListResponse>("/api/ops/tickets", {
    params: { page, page_size: pageSize },
  });
  return data;
}

export async function getTicket(ticketCode: string): Promise<TicketRead> {
  const { data } = await axiosClient.get<TicketRead>(`/api/ops/tickets/${ticketCode}`);
  return data;
}

export async function getUiFlags(): Promise<UiFlags> {
  const { data } = await axiosClient.get<UiFlags>("/api/ops/ui-flags");
  return data;
}
