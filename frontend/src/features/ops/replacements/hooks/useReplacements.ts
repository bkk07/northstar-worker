import { useMutation } from "@tanstack/react-query";
import { useIdempotencyKey } from "../../auth/hooks/useIdempotencyKey";
import { createReplacement } from "../api/replacementsApi";
import type { ReplacementCreate } from "../../types";

export function useCreateReplacement() {
  const idempotencyKey = useIdempotencyKey();
  const mutation = useMutation({
    mutationFn: (payload: ReplacementCreate) => createReplacement(payload, idempotencyKey),
  });
  return { ...mutation, idempotencyKey };
}
