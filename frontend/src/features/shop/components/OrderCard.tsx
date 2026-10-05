import { motion, useReducedMotion } from "framer-motion";
import { Package } from "lucide-react";
import { Link } from "react-router-dom";
import { formatINR } from "@/shared/lib/format";
import { Badge } from "@/shared/ui/badge";
import { snappyTransition } from "@/shared/ui/motion";
import type { OrderRead } from "../types";

/** Delivery progress derived from order status (placed → shipped → delivered). */
export function deliveryProgress(status: string): { pct: number; label: string } {
  switch (status) {
    case "placed":
      return { pct: 33, label: "Order placed" };
    case "shipped":
      return { pct: 66, label: "Shipped" };
    case "delivered":
      return { pct: 100, label: "Delivered" };
    default:
      return { pct: 50, label: status.split("_").join(" ") };
  }
}

export function OrderCard({ order }: { order: OrderRead }) {
  const reduce = useReducedMotion();
  const progress = deliveryProgress(order.status);
  const itemCount = order.items?.length ?? 0;

  return (
    <motion.article
      aria-label={`Order ${order.code}`}
      initial={reduce ? false : { opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={snappyTransition}
      whileHover={reduce ? undefined : { y: -2 }}
      className="ns-card group overflow-hidden"
    >
      {/* Product visual */}
      <div className="relative flex h-28 items-center justify-center overflow-hidden bg-gradient-to-br from-indigo-50 via-slate-50 to-slate-100">
        <span
          aria-hidden
          className="flex h-14 w-14 items-center justify-center rounded-2xl border border-white bg-white/80 shadow-sm transition-transform duration-200 group-hover:scale-105"
        >
          <Package className="h-7 w-7 text-indigo-500" />
        </span>
        <span className="absolute left-3 top-3">
          <Badge tone={order.status}>{order.status.split("_").join(" ")}</Badge>
        </span>
        <span className="absolute right-3 top-3 rounded-full bg-slate-950/70 px-2 py-0.5 font-mono text-[11px] font-medium text-white">
          {order.code}
        </span>
      </div>

      <div className="ns-card-pad">
        <h2 className="text-[15px] font-semibold tracking-tight">
          <Link
            to={`/shop/orders/${order.code}`}
            className="text-indigo-700 hover:text-indigo-800 hover:underline"
          >
            {order.code}
          </Link>
        </h2>
        <p className="mt-0.5 text-[13px] text-slate-500">
          {itemCount === 0
            ? "No items listed"
            : `${itemCount} item${itemCount === 1 ? "" : "s"} · ${progress.label}`}
        </p>

        {/* Delivery progress bar */}
        <div
          role="progressbar"
          aria-valuenow={progress.pct}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`Delivery progress for ${order.code}: ${progress.label}`}
          className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-100"
        >
          <motion.div
            className="h-full rounded-full bg-indigo-600"
            initial={reduce ? false : { width: 0 }}
            animate={{ width: `${progress.pct}%` }}
            transition={{ ...snappyTransition, duration: 0.5 }}
          />
        </div>

        <dl className="mt-3 grid grid-cols-2 gap-3 border-t border-slate-100 pt-3 text-sm">
          <div>
            <dt className="text-xs font-medium uppercase tracking-wider text-slate-400">Total</dt>
            <dd className="mt-0.5 font-semibold tabular-nums">{formatINR(order.total_paise)}</dd>
          </div>
          <div>
            <dt className="text-xs font-medium uppercase tracking-wider text-slate-400">Paid</dt>
            <dd className="mt-0.5 font-semibold tabular-nums">{formatINR(order.paid_paise)}</dd>
          </div>
        </dl>

        <Link
          to={`/shop/orders/${order.code}`}
          className="mt-3 inline-flex items-center gap-1 text-[13px] font-medium text-indigo-700 hover:underline"
        >
          View details →
        </Link>
      </div>
    </motion.article>
  );
}
