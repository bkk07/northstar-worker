import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useOrders } from "@/features/shop/hooks/useShop";
import { axiosClient } from "@/shared/api/axiosClient";

vi.mock("@/shared/api/axiosClient", () => ({
  axiosClient: { get: vi.fn(), post: vi.fn() },
}));

const get = axiosClient.get as unknown as ReturnType<typeof vi.fn>;

function wrapper({ children }: { children: React.ReactNode }) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

describe("useOrders", () => {
  it("stays disabled without a customer code", () => {
    const { result } = renderHook(() => useOrders(undefined), { wrapper });
    expect(result.current.isPending).toBe(true);
    expect(result.current.fetchStatus).toBe("idle");
    expect(get).not.toHaveBeenCalled();
  });

  it("fetches orders for a customer code", async () => {
    const orders = [{ code: "ORD-1942" }];
    get.mockResolvedValueOnce({ data: orders });
    const { result } = renderHook(() => useOrders("C101"), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(orders);
    expect(get).toHaveBeenCalledWith("/api/shop/orders", {
      params: { customer_code: "C101" },
    });
  });
});
