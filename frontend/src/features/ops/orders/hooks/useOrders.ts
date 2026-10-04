import { useQuery } from "@tanstack/react-query";
import { getOrder } from "../api/ordersApi";

export function useOpsOrder(orderCode?: string) {
  return useQuery({
    queryKey: ["ops", "order", orderCode],
    queryFn: () => getOrder(orderCode ?? ""),
    enabled: !!orderCode,
  });
}
