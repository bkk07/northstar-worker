import { useState } from "react";
import { ErrorState, LoadingState } from "@/shared/ui/feedback";
import { getErrorMessage } from "@/shared/lib/errors";
import { OrderSummary } from "../components/OrderSummary";
import { useOpsOrder } from "../hooks/useOrders";

export default function OrderLookupPage() {
  const [draft, setDraft] = useState("");
  const [code, setCode] = useState<string | undefined>();
  const order = useOpsOrder(code);

  function handleSearch(event: React.FormEvent) {
    event.preventDefault();
    setCode(draft || undefined);
  }

  return (
    <main className="mx-auto max-w-3xl p-8">
      <h1 className="text-2xl font-semibold">Order lookup</h1>
      <form aria-label="Look up order" onSubmit={handleSearch} className="mt-4 flex gap-2">
        <label htmlFor="order-code" className="sr-only">
          Order code
        </label>
        <input
          id="order-code"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Order code (e.g. ORD-1942)"
          className="rounded border px-2 py-1"
        />
        <button type="submit" className="rounded-md bg-slate-900 px-4 py-1 text-sm text-white">
          Look up
        </button>
      </form>
      <div className="mt-4">
        {order.isPending && code && <LoadingState what="order" />}
        {order.isError && <ErrorState message={getErrorMessage(order.error)} />}
        {order.data && <OrderSummary order={order.data} />}
      </div>
    </main>
  );
}
