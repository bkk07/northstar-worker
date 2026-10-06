// Phase 1 shared API shapes (spec §27). Backend remains source of truth;
// these mirror the stable API surface so both UIs stay in sync.
export type Role = "CUSTOMER" | "SUPPORT_AGENT";
export type OrderStatus = "PROCESSING" | "SHIPPED" | "DELIVERED";
export type TicketStatus =
  | "OPEN"
  | "AI_PROCESSING"
  | "WAITING_FOR_CUSTOMER"
  | "WAITING_FOR_HUMAN"
  | "ESCALATED"
  | "RESOLVED"
  | "CLOSED";

export type HealthResponse = { status: string; version: string };
