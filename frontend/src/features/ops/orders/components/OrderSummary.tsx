import { formatINR } from "@/shared/lib/format";
import type { OrderRead } from "../../types";

// Ops-local order display (features never import each other; the shop has
// its own OrderCard for the same backend DTO).
export function OrderSummary({ order }: { order: OrderRead }) {
  return (
    <article aria-label={`Order ${order.code}`} className="rounded-md border p-4">
      <h2 className="font-semibold">{order.code}</h2>
      <p className="text-sm text-slate-600">
        {order.status} · Total {formatINR(order.total_paise)} · Paid {formatINR(order.paid_paise)}
      </p>
      <ul className="mt-2 text-sm">
        {order.items.map((item) => (
          <li key={item.id}>
            {item.title} ({item.sku}) × {item.qty}
          </li>
        ))}
      </ul>
    </article>
  );
}
