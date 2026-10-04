import axios from "axios";

// Render any API failure as one human line: AppError {code,message},
// FastAPI validation {detail}, or a bare HTTP status as fallback.
export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as { message?: unknown; detail?: unknown } | undefined;
    if (typeof data?.message === "string" && data.message) return data.message;
    const detail = data?.detail;
    if (typeof detail === "string" && detail) return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((item) =>
          typeof item === "object" && item !== null && "msg" in item
            ? String((item as { msg: unknown }).msg)
            : JSON.stringify(item),
        )
        .join("; ");
    }
    if (error.response) return `Request failed (${error.response.status})`;
    return error.message || "Network error.";
  }
  return "Something went wrong.";
}
