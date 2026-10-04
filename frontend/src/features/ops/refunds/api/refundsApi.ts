import { axiosClient } from "@/shared/api/axiosClient";
import type { RefundCreate, RefundRead } from "../../types";

export async function createRefund(
  payload: RefundCreate,
  idempotencyKey: string,
): Promise<RefundRead> {
  const { data } = await axiosClient.post<RefundRead>("/api/ops/refunds", payload, {
    headers: { "Idempotency-Key": idempotencyKey },
  });
  return data;
}
