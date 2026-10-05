// Worker Control Center DTOs (mirror the backend worker schemas).

export type TaskRead = {
  id: string;
  text: string;
  mode: string;
  status: string;
  current_state: string;
  scenario_ref: string | null;
  created_by: string;
  created_at: string;
};

export type AuditEventRead = {
  id: string;
  task_id: string;
  run_id: string | null;
  seq: number;
  ts: string;
  node: string | null;
  tool: string | null;
  kind: string;
  status: string | null;
  error_type: string | null;
  retry_count: number;
  duration_ms: number | null;
  policy_result: string | null;
  verification_result: string | null;
  payload: Record<string, unknown>;
};

export type ApprovalRead = {
  id: string;
  task_id: string;
  requested_action: string;
  params: Record<string, unknown>;
  params_hash: string;
  reason: string;
  policy_rule_id: string;
  status: string;
  approver: string | null;
  resolved_at: string | null;
  expires_at: string | null;
  created_at: string;
};

export type ClarificationRead = {
  id: string;
  task_id: string;
  kind: string;
  question: string;
  answer: string | null;
  answered_by: string | null;
  status: string;
  created_at: string;
};

export type MemoryItemRead = {
  id: string;
  run_id: string;
  key: string;
  value: Record<string, unknown>;
  source_type: string;
  source_ref: string;
  trust: string;
  confidence: number | null;
  created_at: string;
};

export type EvidencePacketRead = {
  id: string;
  task_id: string;
  packet: Record<string, unknown>;
  summary: string;
  created_at: string;
};

export type ScreenshotRead = {
  run_id: string;
  label: string;
  path: string;
  created_at: string;
};

export type VerificationRead = {
  id: string;
  run_id: string;
  verdict: string;
  invariants: Record<string, unknown>;
  diff: Record<string, unknown>;
  computed_at: string;
};

export type EnvironmentStatus = {
  backend: string;
  database: string;
  pending_tasks: number;
  pending_approvals: number;
  pending_clarifications: number;
};

export type FaultPlanRead = {
  id: string;
  fault_type: string;
  target: string;
  trigger: Record<string, unknown>;
  params: Record<string, unknown>;
  armed: boolean;
};
