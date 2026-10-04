import { useMutation } from "@tanstack/react-query";
import { useIdempotencyKey } from "../../auth/hooks/useIdempotencyKey";
import { createRefund } from "../api/refundsApi";
import type { RefundCreate } from "../../types";

export function useCreateRefund() {
  const idempotencyKey = useIdempotencyKey();
  const mutation = useMutation({
    mutationFn: (payload: RefundCreate) => createRefund(payload, idempotencyKey),
  });
  return { ...mutation, idempotencyKey };
}
