import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEventSource, type TaskAuditEvent } from "@/shared/hooks/useEventSource";
import {
  answerClarification,
  armFault,
  createTask,
  decideApproval,
  getEnvironmentStatus,
  getTask,
  getTaskEvidence,
  getTaskEvents,
  getTaskMemory,
  getTaskScreenshots,
  getTaskVerification,
  listApprovals,
  listClarifications,
  listTasks,
  resetWorld,
  seedWorld,
} from "../api/workerApi";

export function useWorkerTasks(taskStatus?: string) {
  return useQuery({
    queryKey: ["worker", "tasks", taskStatus ?? "all"],
    queryFn: () => listTasks(50, taskStatus),
  });
}

export function useWorkerTask(taskId?: string) {
  return useQuery({
    queryKey: ["worker", "task", taskId],
    queryFn: () => getTask(taskId ?? ""),
    enabled: !!taskId,
  });
}

export function useCreateTask() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (text: string) => createTask(text),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["worker", "tasks"] }),
  });
}

// History first, then live frames appended (dedupe by gapless seq).
export function useTaskTimeline(taskId?: string) {
  const history = useQuery({
    queryKey: ["worker", "task-events", taskId],
    queryFn: () => getTaskEvents(taskId ?? ""),
    enabled: !!taskId,
  });
  const live = useEventSource<TaskAuditEvent>(taskId ? `/api/tasks/${taskId}/events` : null);
  const seen = new Set((history.data ?? []).map((event) => event.seq));
  const merged = [
    ...(history.data ?? []),
    ...live.events.filter((event) => !seen.has(event.seq)),
  ].sort((a, b) => a.seq - b.seq);
  return { ...history, data: merged, liveStatus: live.status };
}

export function useApprovals() {
  return useQuery({ queryKey: ["worker", "approvals"], queryFn: listApprovals });
}

export function useDecideApproval() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      approvalId,
      decision,
      approver,
    }: {
      approvalId: string;
      decision: "approve" | "reject";
      approver: string;
    }) => decideApproval(approvalId, decision, approver),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["worker", "approvals"] });
      queryClient.invalidateQueries({ queryKey: ["worker", "tasks"] });
    },
  });
}

export function useClarifications() {
  return useQuery({ queryKey: ["worker", "clarifications"], queryFn: listClarifications });
}

export function useAnswerClarification() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      clarificationId,
      answer,
      answeredBy,
    }: {
      clarificationId: string;
      answer: string;
      answeredBy: string;
    }) => answerClarification(clarificationId, answer, answeredBy),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["worker", "clarifications"] });
      queryClient.invalidateQueries({ queryKey: ["worker", "tasks"] });
    },
  });
}

export function useTaskEvidence(taskId?: string) {
  return useQuery({
    queryKey: ["worker", "evidence", taskId],
    queryFn: () => getTaskEvidence(taskId ?? ""),
    enabled: !!taskId,
    retry: false,
  });
}

export function useTaskMemory(taskId?: string) {
  return useQuery({
    queryKey: ["worker", "memory", taskId],
    queryFn: () => getTaskMemory(taskId ?? ""),
    enabled: !!taskId,
  });
}

export function useTaskScreenshots(taskId?: string) {
  return useQuery({
    queryKey: ["worker", "screenshots", taskId],
    queryFn: () => getTaskScreenshots(taskId ?? ""),
    enabled: !!taskId,
  });
}

export function useTaskVerification(taskId?: string) {
  return useQuery({
    queryKey: ["worker", "verification", taskId],
    queryFn: () => getTaskVerification(taskId ?? ""),
    enabled: !!taskId,
  });
}

export function useEnvironmentStatus() {
  return useQuery({
    queryKey: ["worker", "environment"],
    queryFn: getEnvironmentStatus,
    retry: false,
  });
}

export function useArmFault() {
  return useMutation({
    mutationFn: ({ faultType, target }: { faultType: string; target: string }) =>
      armFault(faultType, target),
  });
}

export function useResetWorld() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: resetWorld,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["worker"] }),
  });
}

export function useSeedWorld() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: seedWorld,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["worker"] }),
  });
}
