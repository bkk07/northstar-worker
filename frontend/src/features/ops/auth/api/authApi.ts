import { axiosClient } from "@/shared/api/axiosClient";
import type { LoginResponse } from "../../types";

export async function login(agentName: string): Promise<LoginResponse> {
  const { data } = await axiosClient.post<LoginResponse>("/api/ops/auth/login", {
    agent_name: agentName,
  });
  return data;
}

export async function logout(): Promise<void> {
  await axiosClient.post("/api/ops/auth/logout");
}
