import axios from "axios";

// Single axios instance for the customer app. The Bearer token is
// attached per request from localStorage (Phase 2 persistent session).
export const TOKEN_KEY = "ns_customer_token";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
  timeout: 15000,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export const isApiError = (e: unknown) =>
  axios.isAxiosError(e) ? (e.response?.data ?? e.message) : String(e);

export function apiErrorMessage(e: unknown, fallback: string): string {
  if (axios.isAxiosError(e)) {
    const data = e.response?.data as { message?: string; detail?: string } | undefined;
    if (typeof data?.message === "string") return data.message;
    if (typeof data?.detail === "string") return data.detail;
    if (e.response?.status === 409) return "An account with this email already exists.";
    if (e.response?.status === 401) return "Invalid email or password.";
    if (e.message === "Network Error") return "Cannot reach the API. Is the backend running?";
  }
  return fallback;
}
