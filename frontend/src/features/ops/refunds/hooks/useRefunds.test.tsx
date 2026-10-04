import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useCreateRefund } from "@/features/ops/refunds/hooks/useRefunds";
import { axiosClient } from "@/shared/api/axiosClient";

vi.mock("@/shared/api/axiosClient", () => ({
  axiosClient: { get: vi.fn(), post: vi.fn() },
}));

const post = axiosClient.post as unknown as ReturnType<typeof vi.fn>;

function wrapper({ children }: { children: React.ReactNode }) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

describe("useCreateRefund", () => {
  it("sends one stable idempotency key with the payload", async () => {
    post.mockResolvedValue({ data: { id: "refund-1" } });
    const { result, rerender } = renderHook(() => useCreateRefund(), { wrapper });
    const firstKey = result.current.idempotencyKey;
    expect(firstKey).toMatch(/^[0-9a-f-]{36}$/);
    rerender();
    expect(result.current.idempotencyKey).toBe(firstKey);

    result.current.mutate({ order_code: "ORD-1943", ticket_code: "T-1", amount_paise: 100000 });
    await waitFor(() => expect(post).toHaveBeenCalledOnce());
    expect(post).toHaveBeenCalledWith(
      "/api/ops/refunds",
      { order_code: "ORD-1943", ticket_code: "T-1", amount_paise: 100000 },
      { headers: { "Idempotency-Key": firstKey } },
    );
  });
});
