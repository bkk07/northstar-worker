import { Package } from "lucide-react";
import { formatINR } from "@/shared/lib/format";
import { Badge } from "@/shared/ui/badge";
import type { OrderRead } from "../../types";

// Ops-local order display (features never import each other; the shop has
// its own OrderCard for the same backend DTO).
export function OrderSummary({ order }: { order: OrderRead }) {
  return (
    <article aria-label={`Order ${order.code}`} className="ns-card overflow-hidden">
      <div className="flex items-center gap-3 border-b border-slate-100 px-4 py-3.5 sm:px-5">
        <span
          aria-hidden
          className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-50 to-slate-100"
        >
          <Package className="h-5 w-5 text-indigo-500" />
        </span>
        <div className="min-w-0 flex-1">
          <h2 className="font-mono text-[15px] font-semibold">{order.code}</h2>
          <p className="text-[13px] text-slate-500">
            Total {formatINR(order.total_paise)} · Paid {formatINR(order.paid_paise)}
          </p>
        </div>
        <Badge tone={order.status}>{order.status.split("_").join(" ")}</Badge>
      </div>
      <ul className="divide-y divide-slate-100">
        {order.items.map((item) => (
          <li key={item.id} className="flex items-baseline gap-2 px-4 py-2.5 text-sm sm:px-5">
            <span className="min-w-0 flex-1 truncate font-medium text-slate-900">
              {item.title}{" "}
              <span className="font-mono text-xs font-normal text-slate-400">({item.sku})</span>
            </span>
            <span className="shrink-0 text-[13px] tabular-nums text-slate-500">
              × {item.qty}
            </span>
          </li>
        ))}
      </ul>
    </article>
  );
}
