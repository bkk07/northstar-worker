import type { components } from "@/shared/types/dto";

// Feature-local aliases over GENERATED DTOs only (plan Phase 7 DoD: the
// shop uses generated types, never hand-written duplicates).
export type OrderRead = components["schemas"]["OrderRead"];
export type OrderItemRead = components["schemas"]["OrderItemRead"];
export type TicketRead = components["schemas"]["TicketRead"];
export type ShopTicketCreate = components["schemas"]["ShopTicketCreate"];
export type CustomerRead = components["schemas"]["CustomerRead"];

/** Local form state (UI-only; the wire payload is ShopTicketCreate). */
export interface TicketFormState {
  subject: string;
  body: string;
  category: string;
}
