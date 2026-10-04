import { axiosClient } from "@/shared/api/axiosClient";
import type { CustomerRead } from "../../types";

export async function searchCustomers(query: string): Promise<CustomerRead[]> {
  const { data } = await axiosClient.get<CustomerRead[]>("/api/ops/customers", {
    params: { q: query },
  });
  return data;
}
