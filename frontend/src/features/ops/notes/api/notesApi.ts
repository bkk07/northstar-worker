import { axiosClient } from "@/shared/api/axiosClient";
import type { NoteCreate, NoteRead, ReplyCreate, StatusUpdate } from "../../types";
import type { TicketRead } from "../../types";

function keyHeader(idempotencyKey: string) {
  return { headers: { "Idempotency-Key": idempotencyKey } };
}

export async function createNote(
  ticketCode: string,
  payload: NoteCreate,
  idempotencyKey: string,
): Promise<NoteRead> {
  const { data } = await axiosClient.post<NoteRead>(
    `/api/ops/tickets/${ticketCode}/notes`,
    payload,
    keyHeader(idempotencyKey),
  );
  return data;
}

export async function createReply(
  ticketCode: string,
  payload: ReplyCreate,
  idempotencyKey: string,
): Promise<NoteRead> {
  const { data } = await axiosClient.post<NoteRead>(
    `/api/ops/tickets/${ticketCode}/reply`,
    payload,
    keyHeader(idempotencyKey),
  );
  return data;
}

export async function updateStatus(
  ticketCode: string,
  payload: StatusUpdate,
  idempotencyKey: string,
): Promise<TicketRead> {
  const { data } = await axiosClient.post<TicketRead>(
    `/api/ops/tickets/${ticketCode}/status`,
    payload,
    keyHeader(idempotencyKey),
  );
  return data;
}
