import { axiosClient } from "@/shared/api/axiosClient";
import type {
  ApprovalRead,
  AuditEventRead,
  ClarificationRead,
  EnvironmentStatus,
  EvidencePacketRead,
  FaultPlanRead,
  MemoryItemRead,
  ScreenshotRead,
  TaskRead,
  VerificationRead,
} from "../types";

// One axios call per worker endpoint (hooks own caching/refresh).
export async function listTasks(limit = 50, taskStatus?: string): Promise<TaskRead[]> {
  const { data } = await axiosClient.get<TaskRead[]>("/api/tasks", {
    params: { limit, ...(taskStatus ? { status: taskStatus } : {}) },
  });
  return data;
}

export async function createTask(text: string): Promise<TaskRead> {
  const { data } = await axiosClient.post<TaskRead>("/api/tasks", { text, mode: "explicit" });
  return data;
}

export async function getTask(taskId: string): Promise<TaskRead> {
  const { data } = await axiosClient.get<TaskRead>(`/api/tasks/${taskId}`);
  return data;
}

export async function getTaskEvents(taskId: string): Promise<AuditEventRead[]> {
  const { data } = await axiosClient.get<AuditEventRead[]>(`/api/tasks/${taskId}/events/history`);
  return data;
}

export async function getTaskMemory(taskId: string): Promise<MemoryItemRead[]> {
  const { data } = await axiosClient.get<MemoryItemRead[]>(`/api/tasks/${taskId}/memory`);
  return data;
}

export async function getTaskEvidence(taskId: string): Promise<EvidencePacketRead> {
  const { data } = await axiosClient.get<EvidencePacketRead>(`/api/tasks/${taskId}/evidence`);
  return data;
}

export async function getTaskScreenshots(taskId: string): Promise<ScreenshotRead[]> {
  const { data } = await axiosClient.get<ScreenshotRead[]>(
    `/api/tasks/${taskId}/evidence/screenshots`,
  );
  return data;
}

export async function getTaskVerification(taskId: string): Promise<VerificationRead[]> {
  const { data } = await axiosClient.get<VerificationRead[]>(`/api/tasks/${taskId}/verification`);
  return data;
}

export async function listApprovals(): Promise<ApprovalRead[]> {
  const { data } = await axiosClient.get<ApprovalRead[]>("/api/approvals");
  return data;
}

export async function decideApproval(
  approvalId: string,
  decision: "approve" | "reject",
  approver: string,
): Promise<ApprovalRead> {
  const { data } = await axiosClient.post<ApprovalRead>(
    `/api/approvals/${approvalId}/${decision}`,
    {
      approver,
    },
  );
  return data;
}

export async function listClarifications(): Promise<ClarificationRead[]> {
  const { data } = await axiosClient.get<ClarificationRead[]>("/api/clarifications");
  return data;
}

export async function answerClarification(
  clarificationId: string,
  answer: string,
  answeredBy: string,
): Promise<ClarificationRead> {
  const { data } = await axiosClient.post<ClarificationRead>(
    `/api/clarifications/${clarificationId}/answer`,
    { answer, answered_by: answeredBy },
  );
  return data;
}

export async function getEnvironmentStatus(): Promise<EnvironmentStatus> {
  const { data } = await axiosClient.get<EnvironmentStatus>("/api/environment/status");
  return data;
}

export async function armFault(faultType: string, target: string): Promise<FaultPlanRead> {
  const { data } = await axiosClient.post<FaultPlanRead>("/api/environment/faults", {
    fault_type: faultType,
    target,
    trigger: { nth_call: 1 },
    params: {},
  });
  return data;
}

export async function resetWorld(): Promise<{ world_hash: string }> {
  const { data } = await axiosClient.post<{ world_hash: string }>("/api/environment/reset");
  return data;
}

export async function seedWorld(): Promise<{ counts: Record<string, number>; world_hash: string }> {
  const { data } = await axiosClient.post<{
    counts: Record<string, number>;
    world_hash: string;
  }>("/api/environment/seed");
  return data;
}
