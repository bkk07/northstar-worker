import { useQuery } from "@tanstack/react-query";
import { getTicket, getUiFlags, listTickets } from "../api/ticketsApi";

export function useTicketQueue(page: number) {
  return useQuery({
    queryKey: ["ops", "tickets", page],
    queryFn: () => listTickets(page, 10),
  });
}

export function useTicketDetail(ticketCode?: string) {
  return useQuery({
    queryKey: ["ops", "ticket", ticketCode],
    queryFn: () => getTicket(ticketCode ?? ""),
    enabled: !!ticketCode,
  });
}

export function useUiFlags() {
  return useQuery({
    queryKey: ["ops", "ui-flags"],
    queryFn: getUiFlags,
    staleTime: 30_000,
  });
}
