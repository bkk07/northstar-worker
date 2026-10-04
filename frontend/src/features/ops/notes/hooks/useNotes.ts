import { useMutation } from "@tanstack/react-query";
import { useIdempotencyKey } from "../../auth/hooks/useIdempotencyKey";
import { createNote, createReply, updateStatus } from "../api/notesApi";
import type { NoteCreate, ReplyCreate, StatusUpdate } from "../../types";

export function useCreateNote(ticketCode: string) {
  const idempotencyKey = useIdempotencyKey();
  const mutation = useMutation({
    mutationFn: (payload: NoteCreate) => createNote(ticketCode, payload, idempotencyKey),
  });
  return { ...mutation, idempotencyKey };
}

export function useCreateReply(ticketCode: string) {
  const idempotencyKey = useIdempotencyKey();
  const mutation = useMutation({
    mutationFn: (payload: ReplyCreate) => createReply(ticketCode, payload, idempotencyKey),
  });
  return { ...mutation, idempotencyKey };
}

export function useUpdateStatus(ticketCode: string) {
  const idempotencyKey = useIdempotencyKey();
  const mutation = useMutation({
    mutationFn: (payload: StatusUpdate) => updateStatus(ticketCode, payload, idempotencyKey),
  });
  return { ...mutation, idempotencyKey };
}
