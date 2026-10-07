import axios from "axios";

// Internal console API client. Bearer token attached per request
// from localStorage (Phase 2 persistent staff session).
export const STAFF_TOKEN_KEY = "ns_support_token";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
  timeout: 15000,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(STAFF_TOKEN_KEY);
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export function staffApiErrorMessage(e: unknown, fallback: string): string {
  if (axios.isAxiosError(e)) {
    const data = e.response?.data as { message?: string; detail?: string } | undefined;
    if (typeof data?.message === "string") return data.message;
    if (typeof data?.detail === "string") return data.detail;
    if (e.response?.status === 401) return "Invalid staff email or password.";
    if (e.response?.status === 403) return "This account is not staff. Use a SUPPORT_AGENT login.";
    if (e.message === "Network Error") return "Cannot reach the API. Is the backend running?";
    // Timeouts and server errors previously surfaced as a bare "Chat failed":
    // say what happened and confirm nothing was applied behind the scenes.
    // Technical detail stays in the trace/debug UI, never in this string.
    if (e.code === "ECONNABORTED" || /timeout/i.test(e.message ?? "")) {
      return "The request took too long and was stopped. No customer action was confirmed — please retry.";
    }
    const status = e.response?.status ?? 0;
    if (status >= 500) {
      return "The server hit an error. No customer action was confirmed. Please retry or take over the ticket.";
    }
  }
  return fallback;
}
