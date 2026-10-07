import { useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { ArrowLeft, LifeBuoy, Plus, Send } from "lucide-react";
import { Badge, Button, Card, EmptyState, ErrorState, Input, Skeleton } from "@/components/ui";
import { apiErrorMessage } from "@/lib/api-client";
import { listOrders } from "@/services/shop-api";
import { getTicket, listTickets, raiseTicket, replyToTicket } from "@/services/tickets-api";
import { toast } from "@/stores/toast-store";
import { TICKET_CATEGORIES, type TicketDetail } from "@/types";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("en-IN", {
    day: "numeric",
    month: "short",
    hour: "numeric",
    minute: "2-digit",
  });
}

function categoryLabel(c: string): string {
  return c.charAt(0) + c.slice(1).toLowerCase();
}

export function SupportPage() {
  const tickets = useQuery({ queryKey: ["tickets"], queryFn: listTickets });

  if (tickets.isPending) {
    return (
      <div className="flex flex-col gap-3">
        <h1 className="ns-title">Support tickets</h1>
        {[0, 1].map((i) => (
          <Card key={i}>
            <Skeleton className="h-5 w-40" />
            <Skeleton className="mt-2 h-4 w-2/3" />
          </Card>
        ))}
      </div>
    );
  }
  if (tickets.isError) {
    return (
      <Card>
        <ErrorState
          title="Could not load tickets"
          hint="Start the backend and try again."
          onRetry={() => void tickets.refetch()}
        />
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="ns-row-between">
        <div>
          <h1 className="ns-title">Support tickets</h1>
          <p className="ns-muted">Refund, replacement, return, cancellation, delivery, payment.</p>
        </div>
        <Link to="/tickets/new" className="ns-btn ns-btn-primary ns-btn-sm">
          <Plus size={15} aria-hidden /> Raise a ticket
        </Link>
      </div>
      {(tickets.data ?? []).length === 0 ? (
        <Card>
          <EmptyState
            title="No tickets yet"
            hint="After delivery you can raise a ticket from any order."
            action={<Link to="/orders" className="ns-btn ns-btn-secondary ns-btn-sm">View orders</Link>}
          />
        </Card>
      ) : (
        (tickets.data ?? []).map((t, i) => (
          <motion.div
            key={t.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2, delay: Math.min(i * 0.04, 0.3) }}
          >
            <Link to={`/tickets/${t.id}`}>
              <Card className="transition-shadow hover:shadow-md">
                <div className="ns-row-between">
                  <div className="flex items-center gap-2">
                    <LifeBuoy size={16} aria-hidden className="text-slate-400" />
                    <span className="font-semibold">{t.ticket_number}</span>
                    <Badge>{categoryLabel(t.category)}</Badge>
                  </div>
                  <Badge tone={t.status === "RESOLVED" || t.status === "CLOSED" ? "ok" : "warn"}>{t.status.replace(/_/g, " ")}</Badge>
                </div>
                <p className="mt-1.5 truncate text-sm">{t.subject}</p>
                <div className="ns-muted mt-1 flex flex-wrap gap-x-4 text-sm">
                  {t.order_number ? <span>Order {t.order_number}</span> : null}
                  <span>{t.message_count} message{t.message_count === 1 ? "" : "s"}</span>
                  <span>{formatDate(t.created_at)}</span>
                </div>
              </Card>
            </Link>
          </motion.div>
        ))
      )}
    </div>
  );
}

export function RaiseTicketPage() {
  const nav = useNavigate();
  const [params] = useSearchParams();
  const orders = useQuery({ queryKey: ["orders"], queryFn: listOrders });
  const [subject, setSubject] = useState("");
  const [category, setCategory] = useState("GENERAL");
  const [orderId, setOrderId] = useState(params.get("order_id") ?? "");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (subject.trim().length < 5) {
      setError("Subject needs at least 5 characters.");
      return;
    }
    if (description.trim().length < 10) {
      setError("Please describe the issue (at least 10 characters).");
      return;
    }
    setPending(true);
    setError(null);
    try {
      const ticket = await raiseTicket({
        subject: subject.trim(),
        category,
        description: description.trim(),
        order_id: orderId || null,
      });
      nav(`/tickets/${ticket.id}`);
      toast.ok("Ticket raised. Support will reply here.");
    } catch (err) {
      setError(apiErrorMessage(err, "Could not raise the ticket. Please try again."));
      toast.bad("Could not raise the ticket. Please try again.");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="mx-auto w-full max-w-xl">
      <button className="ns-btn ns-btn-ghost self-start" onClick={() => nav(-1)}>
        <ArrowLeft size={16} aria-hidden /> Back
      </button>
      <Card className="mt-2">
        <h1 className="ns-title">Raise a ticket</h1>
        <p className="ns-muted">Support replies here; AI-assisted resolution arrives in later phases.</p>
        <form className="mt-4 flex flex-col gap-3" onSubmit={onSubmit} noValidate>
          <div>
            <label className="ns-label" htmlFor="t-subject">Subject</label>
            <Input
              id="t-subject"
              placeholder="e.g. Screen arrived cracked"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
            />
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="ns-label" htmlFor="t-category">Issue category</label>
              <select
                id="t-category"
                className="ns-input"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              >
                {TICKET_CATEGORIES.map((c) => (
                  <option key={c} value={c}>{categoryLabel(c)}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="ns-label" htmlFor="t-order">Related order (optional)</label>
              <select
                id="t-order"
                className="ns-input"
                value={orderId}
                onChange={(e) => setOrderId(e.target.value)}
              >
                <option value="">No specific order</option>
                {(orders.data ?? []).map((o) => (
                  <option key={o.id} value={o.id}>
                    {o.order_number} · {o.total_display}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div>
            <label className="ns-label" htmlFor="t-desc">Description</label>
            <textarea
              id="t-desc"
              className="ns-input min-h-28"
              placeholder="What happened? What would you like us to do?"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
          {error ? <p className="text-sm text-red-600" role="alert">{error}</p> : null}
          <Button type="submit" disabled={pending}>
            {pending ? "Submitting…" : "Submit ticket"}
          </Button>
        </form>
      </Card>
    </div>
  );
}

function MessageBubble({ m }: { m: TicketDetail["messages"][number] }) {
  const mine = m.sender_type === "CUSTOMER";
  return (
    <div className={`flex ${mine ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-3.5 py-2.5 text-sm ${
          mine ? "rounded-br-md bg-indigo-600 text-white" : "rounded-bl-md bg-slate-100 text-slate-800"
        }`}
      >
        {!mine ? (
          <p className="mb-0.5 text-[11px] font-semibold uppercase tracking-wider opacity-70">
            {m.sender_type === "AI_AGENT" ? "AI assistant" : m.sender_type === "SYSTEM" ? "System" : "Support"}
          </p>
        ) : null}
        <p className="whitespace-pre-wrap">{m.message}</p>
        <p className={`mt-1 text-[11px] ${mine ? "text-indigo-200" : "text-slate-400"}`}>
          {formatDate(m.created_at)}
        </p>
      </div>
    </div>
  );
}

export function TicketDetailPage() {
  const { id = "" } = useParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const detail = useQuery({
    queryKey: ["ticket", id],
    queryFn: () => getTicket(id),
    refetchInterval: (query) => {
      const data = query.state.data as { status: string } | undefined;
      return data && !["RESOLVED", "CLOSED"].includes(data.status) ? 5000 : false;
    },
  });
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);

  async function onSend(e: React.FormEvent) {
    e.preventDefault();
    if (!draft.trim() || sending) return;
    setSending(true);
    setSendError(null);
    try {
      await replyToTicket(id, draft.trim());
      setDraft("");
      await qc.invalidateQueries({ queryKey: ["ticket", id] });
      await qc.invalidateQueries({ queryKey: ["tickets"] });
      toast.ok("Message sent.");
    } catch (err) {
      setSendError(apiErrorMessage(err, "Could not send the message."));
      toast.bad("Could not send the message.");
    } finally {
      setSending(false);
    }
  }

  if (detail.isPending) {
    return (
      <Card>
        <Skeleton className="h-6 w-48" />
        <div className="mt-4 flex flex-col gap-2">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-12 w-full rounded-2xl" />
          ))}
        </div>
      </Card>
    );
  }
  if (detail.isError) {
    return (
      <Card>
        <ErrorState title="Ticket not found" hint="It may belong to another account." onRetry={() => void detail.refetch()} />
      </Card>
    );
  }

  const t = detail.data;
  const open = !["RESOLVED", "CLOSED"].includes(t.status);
  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-4">
      <button className="ns-btn ns-btn-ghost self-start" onClick={() => nav("/support")}>
        <ArrowLeft size={16} aria-hidden /> All tickets
      </button>
      <div className="ns-row-between">
        <div>
          <h1 className="ns-title">{t.ticket_number}</h1>
          <p className="ns-muted">{t.subject} · raised {formatDate(t.created_at)}</p>
        </div>
        <div className="flex gap-1.5">
          <Badge>{categoryLabel(t.category)}</Badge>
          <Badge tone={open ? "warn" : "ok"}>{t.status}</Badge>
        </div>
      </div>
      {t.related_order ? (
        <Card>
          <div className="ns-row-between text-sm">
            <span>
              Related order <Link to={`/orders/${t.related_order.id}`} className="font-semibold text-indigo-700 hover:underline">
                {t.related_order.order_number}
              </Link>
              <span className="ns-muted"> · {t.related_order.status} · {t.related_order.total_display}</span>
            </span>
          </div>
        </Card>
      ) : null}
      <Card>
        <div className="flex flex-col gap-2.5">
          {t.messages.map((m) => (
            <MessageBubble key={m.id} m={m} />
          ))}
        </div>
        {open ? (
          <form className="mt-4 flex gap-2" onSubmit={onSend}>
            <Input
              placeholder="Write a follow-up…"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              aria-label="Reply to ticket"
            />
            <Button type="submit" disabled={sending || !draft.trim()} aria-label="Send message">
              <Send size={16} aria-hidden />
            </Button>
          </form>
        ) : (
          <p className="ns-muted mt-4 text-center">
            This ticket is {t.status.toLowerCase()}.
            {t.resolution ? ` Resolution: ${t.resolution}` : ""}
          </p>
        )}
        {sendError ? <p className="mt-2 text-sm text-red-600" role="alert">{sendError}</p> : null}
      </Card>
    </div>
  );
}
