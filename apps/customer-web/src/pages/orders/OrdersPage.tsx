import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Circle,
  CreditCard,
  Loader2,
  MapPin,
  Package,
} from "lucide-react";
import { Badge, Button, Card, EmptyState, ErrorState, Input, Skeleton } from "@/components/ui";
import { apiErrorMessage } from "@/lib/api-client";
import { formatPaise } from "@/lib/format";
import { checkout, getOrder, listOrders } from "@/services/shop-api";
import { useCart } from "@/stores/cart-store";
import { toast } from "@/stores/toast-store";
import type { Order, OrderDetail, OrderStatus } from "@/types";

function statusTone(status: OrderStatus): "info" | "ok" | "warn" | "bad" {
  if (status === "DELIVERED") return "ok";
  if (status === "SHIPPED") return "info";
  if (status === "CANCELLED" || status === "RETURNED") return "bad";
  return "warn";
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("en-IN", {
    day: "numeric",
    month: "short",
    hour: "numeric",
    minute: "2-digit",
  });
}

function needsPoll(orders: Order[] | undefined): number | false {
  return orders?.some((o) => o.status === "PROCESSING" || o.status === "SHIPPED") ? 5000 : false;
}

export function OrdersPage() {
  const orders = useQuery({
    queryKey: ["orders"],
    queryFn: listOrders,
    refetchInterval: (data) => needsPoll(data),
  });

  if (orders.isPending) {
    return (
      <div className="flex flex-col gap-3">
        <h1 className="ns-title">Orders</h1>
        {[0, 1].map((i) => (
          <Card key={i}>
            <Skeleton className="h-5 w-32" />
            <div className="mt-2 flex flex-col gap-2">
              <Skeleton className="h-4 w-2/3" />
              <Skeleton className="h-4 w-1/4" />
            </div>
          </Card>
        ))}
      </div>
    );
  }
  if (orders.isError) {
    return (
      <Card>
        <ErrorState
          title="Could not load orders"
          hint="Start the backend and try again."
          onRetry={() => void orders.refetch()}
        />
      </Card>
    );
  }
  if ((orders.data ?? []).length === 0) {
    return (
      <Card>
        <h1 className="ns-title">Orders</h1>
        <EmptyState
          title="No orders yet"
          hint="Checkout creates an order; delivery simulation takes ~1 minute."
          action={<Link to="/products" className="ns-btn ns-btn-secondary ns-btn-sm">Start shopping</Link>}
        />
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <div>
        <h1 className="ns-title">Orders</h1>
        <p className="ns-muted">Live status — processing → shipped → delivered in ~1 minute.</p>
      </div>
      {(orders.data ?? []).map((o, i) => (
        <motion.div
          key={o.id}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2, delay: Math.min(i * 0.04, 0.3) }}
        >
          <Link to={`/orders/${o.id}`}>
            <Card className="transition-shadow hover:shadow-md">
              <div className="ns-row-between">
                <div className="flex items-center gap-2">
                  <Package size={16} aria-hidden className="text-slate-400" />
                  <span className="font-semibold">{o.order_number}</span>
                </div>
                <Badge tone={statusTone(o.status)}>{o.status}</Badge>
              </div>
              <div className="ns-muted mt-1.5 flex flex-wrap gap-x-4 gap-y-0.5 text-sm">
                <span>{o.item_count} item{o.item_count === 1 ? "" : "s"}</span>
                <span>{formatDate(o.ordered_at)}</span>
                <span className="font-semibold text-slate-700">{o.total_display}</span>
              </div>
            </Card>
          </Link>
        </motion.div>
      ))}
    </div>
  );
}

export function OrderDetailPage() {
  const { id = "" } = useParams();
  const nav = useNavigate();
  const detail = useQuery({
    queryKey: ["order", id],
    queryFn: () => getOrder(id),
    refetchInterval: (data) =>
      data && (data.status === "PROCESSING" || data.status === "SHIPPED") ? 5000 : false,
  });

  if (detail.isPending) {
    return (
      <Card>
        <Skeleton className="h-6 w-40" />
        <div className="mt-4 flex flex-col gap-2">
          {[0, 1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-4 w-1/2" />
          ))}
        </div>
      </Card>
    );
  }
  if (detail.isError) {
    return (
      <Card>
        <ErrorState title="Order not found" hint="It may belong to another account." onRetry={() => void detail.refetch()} />
      </Card>
    );
  }

  const o: OrderDetail = detail.data;
  return (
    <div className="flex flex-col gap-4">
      <button className="ns-btn ns-btn-ghost self-start" onClick={() => nav("/orders")}>
        <ArrowLeft size={16} aria-hidden /> All orders
      </button>

      <div className="ns-row-between">
        <div>
          <h1 className="ns-title">Order {o.order_number}</h1>
          <p className="ns-muted">Placed {formatDate(o.ordered_at)} · Payment {o.payment_status}</p>
        </div>
        <Badge tone={statusTone(o.status)}>{o.status}</Badge>
      </div>

      <Card>
        <h2 className="text-sm font-semibold">Delivery tracking</h2>
        <ol className="mt-3 flex flex-col gap-0">
          {o.timeline.map((step, i) => (
            <motion.li
              key={step.key}
              className="flex gap-3"
              initial={{ opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.25, delay: i * 0.08 }}
            >
              <div className="flex flex-col items-center">
                <span className={step.done ? "text-emerald-600" : "text-slate-300"}>
                  {step.done ? <Check size={18} aria-hidden /> : <Circle size={18} aria-hidden />}
                </span>
                {i < o.timeline.length - 1 ? (
                  <span className={`h-6 w-px ${step.done ? "bg-emerald-200" : "bg-slate-200"}`} aria-hidden />
                ) : null}
              </div>
              <div className="pb-4">
                <p className={`text-sm font-semibold ${step.done ? "" : "text-slate-400"}`}>{step.label}</p>
                {step.at ? <p className="ns-muted text-xs">{formatDate(step.at)}</p> : null}
              </div>
            </motion.li>
          ))}
        </ol>
        {o.status === "PROCESSING" || o.status === "SHIPPED" ? (
          <p className="ns-muted flex items-center gap-1.5">
            <Loader2 size={13} aria-hidden className="animate-spin" />
            Live update — estimated delivery {formatDate(o.estimated_delivery)}.
          </p>
        ) : o.status === "DELIVERED" ? (
          <p className="text-sm text-emerald-700">
            Delivered{o.delivered_at ? ` ${formatDate(o.delivered_at)}` : ""}. Enjoy!
          </p>
        ) : (
          <p className="ns-muted text-sm">
            This order was {o.status.toLowerCase()} via customer support.
          </p>
        )}
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <h2 className="text-sm font-semibold">Items ({o.item_count})</h2>
          <ul className="mt-2 flex flex-col gap-2">
            {o.items.map((line) => (
              <li key={line.id} className="ns-row-between text-sm">
                <span>{line.product_name} <span className="ns-muted">× {line.quantity}</span></span>
                <span className="font-semibold">{formatPaise(line.line_total_paise)}</span>
              </li>
            ))}
          </ul>
          <div className="ns-row-between mt-2 border-t border-slate-100 pt-2 text-sm">
            <span className="font-semibold">Total</span>
            <span className="font-bold">{o.total_display}</span>
          </div>
        </Card>
        <div className="flex flex-col gap-4">
          <Card>
            <h2 className="flex items-center gap-1.5 text-sm font-semibold">
              <CreditCard size={14} aria-hidden /> Payment
            </h2>
            <div className="ns-muted mt-1.5 flex flex-col gap-0.5 text-sm">
              <span>Ref {o.payment.payment_reference} · Mock · {o.payment.status}</span>
              <span>{o.payment.amount_display} paid {formatDate(o.payment.paid_at)}</span>
            </div>
          </Card>
          <Card>
            <h2 className="flex items-center gap-1.5 text-sm font-semibold">
              <MapPin size={14} aria-hidden /> Shipping address
            </h2>
            <p className="ns-muted mt-1.5 text-sm">{o.shipping_address}</p>
          </Card>
        </div>
      </div>

      <Card>
        <div className="ns-row-between">
          <div>
            <p className="text-sm font-semibold">Need help with this order?</p>
            <p className="ns-muted">Raise a ticket — refund, replacement, return, delivery, or payment.</p>
          </div>
          <Link to={`/tickets/new?order_id=${o.id}`} className="ns-btn ns-btn-secondary ns-btn-sm">
            Raise a ticket
          </Link>
        </div>
      </Card>
    </div>
  );
}

type CheckoutStage = "form" | "processing" | "success";

export function CheckoutPage() {
  const nav = useNavigate();
  const cart = useCart((s) => s.cart);
  const refreshCart = useCart((s) => s.refresh);
  const [address, setAddress] = useState("");
  const [stage, setStage] = useState<CheckoutStage>("form");
  const [placed, setPlaced] = useState<OrderDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function onPay() {
    if (address.trim().length < 10) {
      setError("Please enter a full shipping address (at least 10 characters).");
      return;
    }
    setStage("processing");
    setError(null);
    const started = Date.now();
    try {
      const order = await checkout(address.trim());
      // Hold the processing view briefly so the demo reads clearly.
      const wait = Math.max(0, 1400 - (Date.now() - started));
      await new Promise((r) => setTimeout(r, wait));
      setPlaced(order);
      setStage("success");
      void refreshCart();
      toast.ok(`Order ${order.order_number} placed.`);
    } catch (err) {
      setStage("form");
      setError(apiErrorMessage(err, "Payment failed. Please try again."));
      toast.bad("Payment failed. Please try again.");
    }
  }

  if (stage === "processing") {
    return (
      <Card className="mx-auto w-full max-w-md text-center">
        <Loader2 size={32} aria-hidden className="mx-auto animate-spin text-indigo-600" />
        <h1 className="ns-title mt-3">Processing payment…</h1>
        <p className="ns-muted mt-1">Confirming your mock payment and placing the order.</p>
      </Card>
    );
  }

  if (stage === "success" && placed) {
    return (
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
        <Card className="mx-auto w-full max-w-md text-center">
          <span className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100 text-emerald-700">
            <Check size={24} aria-hidden />
          </span>
          <h1 className="ns-title mt-3">Payment successful</h1>
          <p className="ns-muted mt-1">
            Order <span className="font-semibold text-slate-700">{placed.order_number}</span> placed
            for {placed.total_display}. It delivers in about a minute.
          </p>
          <div className="mt-4 flex justify-center gap-2">
            <Button onClick={() => nav(`/orders/${placed.id}`)}>
              Track order <ArrowRight size={16} aria-hidden />
            </Button>
            <Button variant="secondary" onClick={() => nav("/products")}>
              Continue shopping
            </Button>
          </div>
        </Card>
      </motion.div>
    );
  }

  const items = cart?.items ?? [];
  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
      <Card>
        <h1 className="ns-title">Checkout</h1>
        <p className="ns-muted">Mock payment — no real money moves.</p>
        <label className="ns-label mt-4" htmlFor="address">Shipping address</label>
        <Input
          id="address"
          placeholder="Flat, street, city, PIN…"
          value={address}
          onChange={(e) => setAddress(e.target.value)}
        />
        {error ? <p className="mt-2 text-sm text-red-600" role="alert">{error}</p> : null}
        <div className="mt-4 flex gap-2">
          <Button onClick={() => void onPay()} disabled={items.length === 0}>
            Pay{cart ? ` ${cart.total_paise > 0 ? formatPaise(cart.total_paise) : ""}` : ""}
          </Button>
          <Button variant="secondary" onClick={() => nav("/cart")}>Back to cart</Button>
        </div>
      </Card>
      <Card>
        <h2 className="ns-title">Summary</h2>
        {items.length === 0 ? (
          <p className="ns-muted mt-2">Your cart is empty.</p>
        ) : (
          <ul className="mt-2 flex flex-col gap-1.5 text-sm">
            {items.map((line) => (
              <li key={line.id} className="ns-row-between">
                <span>{line.product_name} <span className="ns-muted">× {line.quantity}</span></span>
                <span className="font-semibold">{formatPaise(line.line_total_paise)}</span>
              </li>
            ))}
          </ul>
        )}
        <div className="ns-row-between mt-2 border-t border-slate-100 pt-2 text-sm">
          <span className="font-semibold">Total</span>
          <span className="font-bold">{cart ? formatPaise(cart.total_paise) : "—"}</span>
        </div>
      </Card>
    </div>
  );
}
