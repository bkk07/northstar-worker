import { useState } from "react";
import { Search } from "lucide-react";
import { ErrorState, LoadingState } from "@/shared/ui/feedback";
import { getErrorMessage } from "@/shared/lib/errors";
import { PageHeader } from "@/shared/ui/page-header";
import { Card, CardBody, CardHeader } from "@/shared/ui/card";
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
    <main className="ns-page space-y-5">
      <PageHeader
        eyebrow="Ops console"
        title="Order lookup"
        desc="Lines and totals straight from the source of truth — confirm ownership before mutating."
      />
      <Card lift={false}>
        <CardHeader title="Find an order" desc="Human order code, e.g. ORD-1942." />
        <CardBody>
          <form aria-label="Look up order" onSubmit={handleSearch} className="flex max-w-lg gap-2">
            <div className="relative flex-1">
              <label htmlFor="order-code" className="sr-only">
                Order code
              </label>
              <Search
                aria-hidden
                className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
              />
              <input
                id="order-code"
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                placeholder="Order code (e.g. ORD-1942)"
                autoComplete="off"
                className="ns-input pl-9"
              />
            </div>
            <button type="submit" className="ns-btn ns-btn-primary shrink-0">
              Look up
            </button>
          </form>
        </CardBody>
      </Card>
      <div>
        {order.isPending && code && <LoadingState what="order" />}
        {order.isError && <ErrorState message={getErrorMessage(order.error)} />}
        {order.data && <OrderSummary order={order.data} />}
      </div>
    </main>
  );
}
