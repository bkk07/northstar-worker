import { Link } from "react-router-dom";
import { formatINR } from "@/shared/lib/format";
import type { OrderRead } from "../types";

export function OrderCard({ order }: { order: OrderRead }) {
  return (
    <article aria-label={`Order ${order.code}`} className="rounded-md border p-4">
      <h2 className="font-semibold">
        <Link to={`/shop/orders/${order.code}`} className="underline">
          {order.code}
        </Link>
      </h2>
      <dl className="mt-2 grid grid-cols-2 gap-1 text-sm">
        <dt className="text-slate-500">Status</dt>
        <dd>{order.status}</dd>
        <dt className="text-slate-500">Total</dt>
        <dd>{formatINR(order.total_paise)}</dd>
        <dt className="text-slate-500">Paid</dt>
        <dd>{formatINR(order.paid_paise)}</dd>
      </dl>
    </article>
  );
}
