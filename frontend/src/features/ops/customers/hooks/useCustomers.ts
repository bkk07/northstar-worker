import { useQuery } from "@tanstack/react-query";
import { searchCustomers } from "../api/customersApi";

export function useCustomerSearch(query: string) {
  return useQuery({
    queryKey: ["ops", "customers", query],
    queryFn: () => searchCustomers(query),
    enabled: query.trim().length > 0,
  });
}
