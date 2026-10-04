import { describe, expect, it } from "vitest";
import { getErrorMessage } from "@/shared/lib/errors";
import { AxiosError, AxiosHeaders } from "axios";

function axiosError(data: unknown, status = 422): AxiosError {
  const error = new AxiosError("failed");
  error.response = {
    data,
    status,
    statusText: "",
    headers: {},
    config: { headers: new AxiosHeaders() },
  };
  return error;
}

describe("getErrorMessage", () => {
  it("reads AppError bodies", () => {
    expect(getErrorMessage(axiosError({ code: "CONFLICT", message: "already replaced" }))).toBe(
      "already replaced",
    );
  });

  it("reads FastAPI validation details", () => {
    expect(
      getErrorMessage(axiosError({ detail: [{ msg: "field required" }, { msg: "bad value" }] })),
    ).toBe("field required; bad value");
  });

  it("falls back to the status", () => {
    expect(getErrorMessage(axiosError({}, 500))).toBe("Request failed (500)");
  });
});
