import { Link } from "react-router-dom";
import { Card } from "@/components/ui";
import type { ConsoleTicketDetail } from "@/services/support-api";

export function ContextPanel({ t }: { t: ConsoleTicketDetail }) {
  return (
    <div className="flex flex-col gap-4">
      <Card>
        <p className="sp-muted mb-1 text-xs font-semibold uppercase tracking-wider">Customer</p>
        <p className="text-sm font-semibold">{t.customer.name}</p>
        <p className="sp-muted text-[13px]">{t.customer.email}</p>
      </Card>

      {t.related_order ? (
        <Card>
          <p className="sp-muted mb-1 text-xs font-semibold uppercase tracking-wider">
            Order {t.related_order.order_number} · {t.related_order.status.toLowerCase()}
          </p>
          <ul className="flex flex-col gap-1 text-[13px]">
            {t.related_order.items.map((line, i) => (
              <li key={i} className="ns-row-between">
                <span>{line.product_name} × {line.quantity}</span>
                <span className="sp-muted">₹{(line.line_total_paise / 100).toLocaleString("en-IN")}</span>
              </li>
            ))}
          </ul>
          <p className="sp-muted mt-1.5 text-[13px]">
            {t.related_order.total_display} · {t.related_order.payment_status}
            {t.related_order.payment_reference ? ` · ${t.related_order.payment_reference}` : ""}
          </p>
          <p className="sp-muted mt-0.5 text-[13px]">Ordered {new Date(t.related_order.ordered_at).toLocaleDateString()}</p>
          <p className="sp-muted mt-0.5 text-[13px]">{t.related_order.shipping_address}</p>
        </Card>
      ) : (
        <Card><p className="sp-muted text-[13px]">No linked order.</p></Card>
      )}

      {t.policies.length > 0 ? (
        <Card>
          <p className="sp-muted mb-1 text-xs font-semibold uppercase tracking-wider">Product policy</p>
          <ul className="flex flex-col gap-1.5 text-[13px] text-slate-600">
            {t.policies.map((p) => (
              <li key={p.product_name}>
                <span className="font-medium text-slate-800">{p.product_name}:</span> {p.summary}
                <span className="sp-muted block text-xs">
                  return {p.return_allowed ? "allowed" : "not allowed"} · refund{" "}
                  {p.refund_allowed ? "allowed" : "not allowed"} · cancel{" "}
                  {p.cancellation_allowed ? "allowed" : "not allowed"}
                </span>
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      <Card>
        <p className="sp-muted mb-1 text-xs font-semibold uppercase tracking-wider">Recent orders</p>
        {t.recent_orders.length === 0 ? (
          <p className="sp-muted text-[13px]">None.</p>
        ) : (
          <ul className="flex flex-col gap-1 text-[13px]">
            {t.recent_orders.map((o) => (
              <li key={o.id} className="ns-row-between">
                <span>{o.order_number}</span>
                <span className="sp-muted">{o.status.toLowerCase()} · {o.total_display}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card>
        <p className="sp-muted mb-1 text-xs font-semibold uppercase tracking-wider">Previous tickets</p>
        {t.previous_tickets.length === 0 ? (
          <p className="sp-muted text-[13px]">None.</p>
        ) : (
          <ul className="flex flex-col gap-1 text-[13px]">
            {t.previous_tickets.map((p) => (
              <li key={p.id}>
                <Link to={`/tickets/${p.id}`} className="text-indigo-700 hover:underline">
                  {p.ticket_number}
                </Link>
                <span className="sp-muted"> · {p.subject} · {p.status.toLowerCase()}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
