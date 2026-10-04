import { axiosClient } from "@/shared/api/axiosClient";
import type { OrderRead } from "../../types";

export async function getOrder(orderCode: string): Promise<OrderRead> {
  const { data } = await axiosClient.get<OrderRead>(`/api/ops/orders/${orderCode}`);
  return data;
}
