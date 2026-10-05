import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { PackageSearch, Search } from "lucide-react";
import { OrderCard } from "../components/OrderCard";
import { ErrorState, LoadingState } from "@/shared/ui/feedback";
import { EmptyState } from "@/shared/ui/empty-state";
import { PageEnter, PageEnterItem } from "@/shared/ui/page-header";
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
    <main className="ns-page space-y-6">
      {/* Hero header with order search */}
      <section className="relative overflow-hidden rounded-2xl bg-slate-950 px-6 py-8 text-white sm:px-8">
        <div
          aria-hidden
          className="pointer-events-none absolute -right-20 -top-20 h-64 w-64 rounded-full bg-indigo-600/30 blur-3xl"
        />
        <div
          aria-hidden
          className="pointer-events-none absolute -bottom-24 left-1/3 h-56 w-56 rounded-full bg-indigo-500/20 blur-3xl"
        />
        <div className="relative">
          <p className="text-xs font-semibold uppercase tracking-[0.1em] text-indigo-300">
            Northstar Shop
          </p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight sm:text-3xl">
            Track, manage &amp; get help with your orders
          </h1>
          <p className="mt-1.5 max-w-xl text-sm leading-6 text-slate-400">
            Look up orders by customer code, follow delivery progress, and raise a
            support ticket when something is wrong.
          </p>
          <form
            aria-label="Find orders"
            onSubmit={handleSearch}
            className="mt-5 flex max-w-lg gap-2"
          >
            <div className="relative flex-1">
              <label htmlFor="customer-code" className="sr-only">
                Customer code
              </label>
              <Search
                aria-hidden
                className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
              />
              <input
                id="customer-code"
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                placeholder="Customer code (e.g. C101)"
                autoComplete="off"
                className="w-full rounded-xl border border-white/15 bg-white/10 py-2.5 pl-9 pr-3 text-sm text-white placeholder:text-slate-500 backdrop-blur focus:border-indigo-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
              />
            </div>
            <button type="submit" className="ns-btn ns-btn-primary shrink-0">
              Find orders
            </button>
          </form>
        </div>
      </section>

      {orders.isPending && customerCode && <LoadingState what="orders" />}
      {orders.isError && <ErrorState message="Could not load orders." />}
      {orders.data &&
        (orders.data.length === 0 ? (
          <EmptyState
            title="No orders found"
            desc={`Nothing on file for ${customerCode ?? "this customer"}. Check the code and try again.`}
            icon={PackageSearch}
            action={
              <button
                type="button"
                onClick={() => {
                  setDraft("C101");
                  setParams({ customer_code: "C101" });
                }}
                className="ns-btn ns-btn-secondary ns-btn-sm"
              >
                Load demo customer C101
              </button>
            }
          />
        ) : (
          <PageEnter className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {orders.data.map((order) => (
              <PageEnterItem key={order.id}>
                <OrderCard order={order} />
              </PageEnterItem>
            ))}
          </PageEnter>
        ))}
    </main>
  );
}
