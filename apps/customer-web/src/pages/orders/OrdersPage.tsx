import { Link } from "react-router-dom";
import { useParams } from "react-router-dom";
import { Card, Badge, EmptyState } from "@/components/ui";

// Phase 1: orders shell. Timeline UI arrives Phase 4; ticket CTA Phase 5.
export function OrdersPage() {
  return (
    <Card>
      <div className="ns-row-between">
        <h1 className="ns-title">Orders</h1>
        <Badge>Phase 4</Badge>
      </div>
      <EmptyState
        title="No orders yet"
        hint="Checkout creates an order in Phase 4; delivery simulation takes ~1 minute."
        action={<Link to="/products" className="ns-btn ns-btn-secondary ns-btn-sm">Start shopping</Link>}
      />
    </Card>
  );
}

export function OrderDetailPage() {
  const { id } = useParams();
  return (
    <Card>
      <Badge>Phase 4 · {id}</Badge>
      <h1 className="ns-title mt-2">Order timeline</h1>
      <ol className="mt-3 flex flex-col gap-2 text-sm text-slate-600">
        {["Order placed", "Payment confirmed", "Processing", "Shipped", "Delivered"].map((s) => (
          <li key={s} className="flex items-center gap-2">
            <span aria-hidden>○</span> {s}
          </li>
        ))}
      </ol>
      <p className="ns-muted mt-3">Need help with this order? Ticket CTA arrives in Phase 5.</p>
    </Card>
  );
}
