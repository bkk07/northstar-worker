import { axiosClient } from "@/shared/api/axiosClient";
import type { ReplacementCreate, ReplacementRead } from "../../types";

export async function createReplacement(
  payload: ReplacementCreate,
  idempotencyKey: string,
): Promise<ReplacementRead> {
  const { data } = await axiosClient.post<ReplacementRead>("/api/ops/replacements", payload, {
    headers: { "Idempotency-Key": idempotencyKey },
  });
  return data;
}
