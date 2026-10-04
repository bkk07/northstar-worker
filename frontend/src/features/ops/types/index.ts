import type { components } from "@/shared/types/dto";

// Ops feature aliases over GENERATED DTOs only (no hand-written duplicates).
export type CustomerRead = components["schemas"]["CustomerRead"];
export type OrderRead = components["schemas"]["OrderRead"];
export type TicketRead = components["schemas"]["TicketRead"];
export type TicketListResponse = components["schemas"]["TicketListResponse"];
export type ReplacementRead = components["schemas"]["ReplacementRead"];
export type ReplacementCreate = components["schemas"]["ReplacementCreate"];
export type RefundRead = components["schemas"]["RefundRead"];
export type RefundCreate = components["schemas"]["RefundCreate"];
export type NoteRead = components["schemas"]["NoteRead"];
export type NoteCreate = components["schemas"]["NoteCreate"];
export type ReplyCreate = components["schemas"]["ReplyCreate"];
export type StatusUpdate = components["schemas"]["StatusUpdate"];
export type UiFlags = components["schemas"]["UiFlags"];
export type LoginRequest = components["schemas"]["LoginRequest"];
export type LoginResponse = components["schemas"]["LoginResponse"];
