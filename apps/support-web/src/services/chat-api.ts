import { api } from "@/lib/api-client";

export type ChatAction = {
  kind: string;
  label: string;
  task_id?: string | null;
  href?: string | null;
  approval_id?: string | null;
  decision?: string | null;
};

export type ChatReply = {
  reply: string;
  task_id?: string | null;
  ticket_id?: string | null;
  actions: ChatAction[];
};

export type WorkerTaskStatus = {
  id: string;
  status: string;
  text: string;
};

// One call per chat turn. The backend routes intent deterministically and
// may create + launch a worker task (solve flow). Recent thread texts ride
// along so follow-ups ("yes, look at that ticket") resolve against codes
// mentioned earlier. Staff token is attached by the shared api client;
// /api/chat itself is operator-scoped.
export async function postSupportChat(message: string, history: string[] = []): Promise<ChatReply> {
  // Model-backed turns can legitimately take a while; the shared client
  // times out at 15s, so chat gets its own budget (server falls back to
  // the deterministic draft past ~10s anyway).
  const { data } = await api.post<ChatReply>("/api/chat", { message, history }, { timeout: 45000 });
  return data;
}

export async function fetchWorkerTask(taskId: string): Promise<WorkerTaskStatus> {
  const { data } = await api.get<WorkerTaskStatus>(`/api/tasks/${taskId}`);
  return data;
}

export type WorkerTaskEvidence = { summary: string };

export type TaskAuditEvent = {
  kind: string;
  node: string | null;
  tool: string | null;
  status: string | null;
};

export async function fetchTaskEvents(taskId: string): Promise<TaskAuditEvent[]> {
  try {
    const { data } = await api.get<TaskAuditEvent[]>(`/api/tasks/${taskId}/events/history`);
    return data;
  } catch {
    return [];
  }
}

export async function fetchTaskEvidence(taskId: string): Promise<WorkerTaskEvidence | null> {
  try {
    const { data } = await api.get<WorkerTaskEvidence>(`/api/tasks/${taskId}/evidence`);
    return data;
  } catch {
    // No packet (e.g. the run crashed before reporting) — caller falls back.
    return null;
  }
}

export type PendingClarification = {
  id: string;
  task_id: string;
  kind: string;
  question: string;
  status: string;
};

export async function fetchPendingClarifications(): Promise<PendingClarification[]> {
  try {
    const { data } = await api.get<PendingClarification[]>("/api/clarifications");
    return data;
  } catch {
    return [];
  }
}

export async function answerClarification(
  id: string,
  answer: string,
  answeredBy: string,
): Promise<unknown> {
  const { data } = await api.post(`/api/clarifications/${id}/answer`, {
    answer,
    answered_by: answeredBy,
  });
  return data;
}
export async function decideWorkerApproval(
  approvalId: string,
  decision: "approve" | "reject",
  approver: string,
): Promise<unknown> {
  const { data } = await api.post(`/api/approvals/${approvalId}/${decision}`, {
    approver,
  });
  return data;
}
