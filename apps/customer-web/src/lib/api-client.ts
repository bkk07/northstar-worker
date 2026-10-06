import axios from "axios";

// Single axios instance for the customer app. Backend arrives in Phase 2;
// until then every page renders professional loading/empty/error states.
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
  timeout: 15000,
});

export const isApiError = (e: unknown) =>
  axios.isAxiosError(e) ? (e.response?.data ?? e.message) : String(e);
