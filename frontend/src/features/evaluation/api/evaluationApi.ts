import { axiosClient } from "@/shared/api/axiosClient";
import type { EvalRunDetail, EvalRunRead, EvalScenarioRead } from "../types";

// One axios call per evaluation endpoint (hooks own caching).
export async function listEvalRuns(limit = 20): Promise<EvalRunRead[]> {
  const { data } = await axiosClient.get<EvalRunRead[]>("/api/eval/runs", {
    params: { limit },
  });
  return data;
}

export async function getEvalRun(runId: string): Promise<EvalRunDetail> {
  const { data } = await axiosClient.get<EvalRunDetail>(`/api/eval/runs/${runId}`);
  return data;
}

export async function listEvalScenarios(suite = "seeded"): Promise<EvalScenarioRead[]> {
  const { data } = await axiosClient.get<EvalScenarioRead[]>("/api/eval/scenarios", {
    params: { suite },
  });
  return data;
}
