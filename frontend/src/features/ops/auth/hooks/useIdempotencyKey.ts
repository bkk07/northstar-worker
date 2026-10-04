import { useRef } from "react";

// One idempotency key per form instance: double submits replay server-side
// (the backend returns the existing entity for a known key).
export function useIdempotencyKey() {
  const ref = useRef<string | null>(null);
  if (ref.current === null) ref.current = crypto.randomUUID();
  return ref.current;
}
