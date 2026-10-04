import axios from "axios";

// Single configured client for the whole app (feature api/ modules import this).
// Same-origin relative URLs in dev (Vite proxies /api → backend, avoiding CORS);
// VITE_API_URL overrides in prod.
export const apiBaseUrl = import.meta.env.VITE_API_URL ?? "";

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
