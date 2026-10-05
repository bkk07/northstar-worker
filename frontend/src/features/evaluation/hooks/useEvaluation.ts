import { useQuery } from "@tanstack/react-query";
import { getEvalRun, listEvalRuns, listEvalScenarios } from "../api/evaluationApi";

export function useEvalRuns(limit = 20) {
  return useQuery({
    queryKey: ["evaluation", "runs", limit],
    queryFn: () => listEvalRuns(limit),
  });
}

export function useEvalRun(runId?: string) {
  return useQuery({
    queryKey: ["evaluation", "run", runId],
    queryFn: () => getEvalRun(runId ?? ""),
    enabled: !!runId,
  });
}

export function useEvalScenarios() {
  return useQuery({
    queryKey: ["evaluation", "scenarios"],
    queryFn: listEvalScenarios,
  });
}
