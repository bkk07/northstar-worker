import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { OrderCard } from "../components/OrderCard";
import { ErrorState, LoadingState } from "../components/Feedback";
import { useOrders } from "../hooks/useShop";

export default function ShopOrdersPage() {
  const [params, setParams] = useSearchParams();
  const [draft, setDraft] = useState(params.get("customer_code") ?? "C101");
  const customerCode = params.get("customer_code") ?? undefined;
  const orders = useOrders(customerCode);

  function handleSearch(event: React.FormEvent) {
    event.preventDefault();
    setParams(draft ? { customer_code: draft } : {});
  }

  return (
    <main className="mx-auto max-w-3xl p-8">
      <h1 className="text-2xl font-semibold">Your orders</h1>
      <form aria-label="Find orders" onSubmit={handleSearch} className="mt-4 flex gap-2">
        <label htmlFor="customer-code" className="sr-only">
          Customer code
        </label>
        <input
          id="customer-code"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Customer code (e.g. C101)"
          className="rounded border px-2 py-1"
        />
        <button type="submit" className="rounded-md bg-slate-900 px-4 py-1 text-sm text-white">
          Find orders
        </button>
      </form>
      {orders.isPending && customerCode && <LoadingState what="orders" />}
      {orders.isError && <ErrorState message="Could not load orders." />}
      {orders.data && (
        <div className="mt-4 space-y-3">
          {orders.data.length === 0 && <p className="text-sm">No orders found.</p>}
          {orders.data.map((order) => (
            <OrderCard key={order.id} order={order} />
          ))}
        </div>
      )}
    </main>
  );
}
