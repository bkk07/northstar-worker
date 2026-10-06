import { useMutation, useQuery } from "@tanstack/react-query";
import {
  createTicket,
  getCustomer,
  getOrder,
  getTicket,
  listOrders,
  listOrderTickets,
} from "../api/shopApi";

// TanStack Query owns all server state; components read these hooks.
export function useOrders(customerCode?: string) {
  return useQuery({
    queryKey: ["shop", "orders", customerCode ?? ""],
    queryFn: () => listOrders(customerCode),
    enabled: !!customerCode,
  });
}

export function useOrder(orderCode?: string) {
  return useQuery({
    queryKey: ["shop", "order", orderCode],
    queryFn: () => getOrder(orderCode ?? ""),
    enabled: !!orderCode,
  });
}

export function useTicket(ticketCode?: string) {
  return useQuery({
    queryKey: ["shop", "ticket", ticketCode],
    queryFn: () => getTicket(ticketCode ?? ""),
    enabled: !!ticketCode,
  });
}

export function useOrderTickets(orderCode?: string) {
  return useQuery({
    queryKey: ["shop", "order-tickets", orderCode],
    queryFn: () => listOrderTickets(orderCode ?? ""),
    enabled: !!orderCode,
  });
}

export function useCreateTicket() {
  return useMutation({ mutationFn: createTicket });
}

export function useCustomer(customerId?: string) {
  return useQuery({
    queryKey: ["shop", "customer", customerId],
    queryFn: () => getCustomer(customerId ?? ""),
    enabled: !!customerId,
  });
}
