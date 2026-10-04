import axios from "axios";

// Single configured client for the whole app (feature api/ modules import this).
// Vite proxy forwards /api → backend in dev; VITE_API_URL overrides in prod.
export const apiBaseUrl =
  import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

export const axiosClient = axios.create({
  baseURL: apiBaseUrl,
  timeout: 10_000,
  headers: { "Content-Type": "application/json" },
});

export type HealthResponse = {
  status: string;
  service: string;
  version: string;
};

export async function fetchHealth(): Promise<HealthResponse> {
  const { data } = await axiosClient.get<HealthResponse>("/api/health");
  return data;
}
