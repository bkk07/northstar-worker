import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Package } from "lucide-react";
import { TicketForm } from "../components/TicketForm";
import { deliveryProgress } from "../components/OrderCard";
import { ErrorState, LoadingState } from "@/shared/ui/feedback";
import { Badge } from "@/shared/ui/badge";
import { Card, CardBody, CardHeader } from "@/shared/ui/card";
import { PageEnter, PageEnterItem } from "@/shared/ui/page-header";
import { useCustomer, useOrder, useOrderTickets } from "../hooks/useShop";
import { formatINR } from "@/shared/lib/format";

export default function ShopOrderDetailPage() {
  const { orderCode } = useParams();
  const navigate = useNavigate();
  const order = useOrder(orderCode);
  const customer = useCustomer(order.data?.customer_id);
  const tickets = useOrderTickets(orderCode);

  if (order.isPending)
    return (
      <main className="ns-page-narrow">
        <LoadingState what="order" />
      </main>
    );
  if (order.isError || !order.data)
    return (
      <main className="ns-page-narrow">
        <ErrorState message="Could not load the order." />
      </main>
    );

  const progress = deliveryProgress(order.data.status);

  return (
    <main className="ns-page-narrow space-y-5">
      <button
        type="button"
        onClick={() => navigate("/shop/orders")}
        className="inline-flex items-center gap-1 text-[13px] font-medium text-slate-500 hover:text-slate-900"
      >
        <ArrowLeft aria-hidden className="h-3.5 w-3.5" />
        All orders
      </button>

      <PageEnter className="space-y-5">
        {/* Order hero */}
        <PageEnterItem>
          <Card lift={false}>
            <CardBody>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.08em] text-indigo-600">
                    Order detail
                  </p>
                  <h1 className="mt-1 text-2xl font-semibold tracking-tight">
                    Order {order.data.code}
                  </h1>
                  <p className="mt-1 text-sm text-slate-500">
                    Total {formatINR(order.data.total_paise)} · Paid{" "}
                    {formatINR(order.data.paid_paise)}
                    {order.data.delivered_at
                      ? ` · Delivered ${new Date(order.data.delivered_at).toLocaleDateString()}`
                      : ""}
                  </p>
                </div>
                <Badge tone={order.data.status}>
                  {order.data.status.split("_").join(" ")}
                </Badge>
              </div>
              <div
                role="progressbar"
                aria-valuenow={progress.pct}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label={`Delivery progress: ${progress.label}`}
                className="mt-4 h-2 overflow-hidden rounded-full bg-slate-100"
              >
                <div
                  className="h-full rounded-full bg-indigo-600"
                  style={{ width: `${progress.pct}%` }}
                />
              </div>
              <p className="mt-1.5 text-xs font-medium text-slate-500">{progress.label}</p>
            </CardBody>
          </Card>
        </PageEnterItem>

        {/* Items as product rows */}
        <PageEnterItem>
          <Card lift={false}>
            <CardHeader
              title={`Items (${order.data.items.length})`}
              desc="Everything in this shipment."
            />
            <ul className="divide-y divide-slate-100">
              {order.data.items.map((item) => (
                <li key={item.id} className="flex items-center gap-3 px-4 py-3 sm:px-5">
                  <span
                    aria-hidden
                    className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-50 to-slate-100"
                  >
                    <Package className="h-5 w-5 text-indigo-500" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium text-slate-900">
                      {item.title}
                    </span>
                    <span className="block font-mono text-xs text-slate-400">
                      {item.sku} · {item.category}
                    </span>
                  </span>
                  <span className="shrink-0 text-[13px] text-slate-500">× {item.qty}</span>
                  <span className="shrink-0 text-sm font-semibold tabular-nums">
                    {formatINR(item.unit_paise)}
                  </span>
                </li>
              ))}
            </ul>
          </Card>
        </PageEnterItem>

        {/* Tickets raised against this order */}
        <PageEnterItem>
          <Card lift={false}>
            <CardHeader
              title={`Tickets (${tickets.data?.length ?? "…"})`}
              desc="Support history for this order."
            />
            {tickets.isPending && (
              <p className="px-4 py-3 text-[13px] text-slate-500 sm:px-5">Loading tickets…</p>
            )}
            {tickets.data && tickets.data.length === 0 && (
              <p className="px-4 py-3 text-[13px] text-slate-500 sm:px-5">
                No tickets yet — raise one below if something is wrong.
              </p>
            )}
            {tickets.data && tickets.data.length > 0 && (
              <ul className="divide-y divide-slate-100">
                {tickets.data.map((ticket) => (
                  <li key={ticket.id} className="px-4 py-3 sm:px-5">
                    <p className="flex items-center justify-between gap-2">
                      <Link
                        to={`/shop/tickets/${ticket.code}`}
                        className="text-sm font-semibold text-indigo-700 hover:underline"
                      >
                        {ticket.code}
                      </Link>
                      <Badge tone={ticket.status}>{ticket.status}</Badge>
                    </p>
                    <p className="mt-0.5 truncate text-[13px] text-slate-600">
                      {ticket.subject}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </PageEnterItem>

        {/* Raise a ticket */}
        {customer.data && (
          <PageEnterItem>
            <TicketForm
              customerCode={customer.data.code}
              orderCode={order.data.code}
              onCreated={(ticket) => navigate(`/shop/tickets/${ticket.code}`)}
            />
          </PageEnterItem>
        )}
      </PageEnter>
    </main>
  );
}
