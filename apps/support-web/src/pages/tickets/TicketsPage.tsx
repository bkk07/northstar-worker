import { useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, LifeBuoy, Search, Send, StickyNote } from "lucide-react";
import { Badge, Button, Card, EmptyState, ErrorState, Input } from "@/components/ui";
import { staffApiErrorMessage } from "@/lib/api-client";
import {
  addInternalNote,
  escalateTicket,
  fetchQueue,
  fetchTicketDetail,
  replyToTicket,
  resolveTicket,
  type ConsoleMessage,
} from "@/services/support-api";

const STATUS_TABS = ["ALL", "OPEN", "ESCALATED", "RESOLVED", "CLOSED"] as const;
const PRIORITIES = ["ALL", "LOW", "NORMAL", "HIGH", "URGENT"] as const;

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("en-IN", {
    day: "numeric",
    month: "short",
    hour: "numeric",
    minute: "2-digit",
  });
}

function statusTone(status: string): "info" | "ok" | "warn" | "bad" {
  if (status === "OPEN") return "warn";
  if (status === "ESCALATED" || status === "CANCELLED" || status === "RETURNED") return "bad";
  if (status === "RESOLVED") return "ok";
  return "info";
}

function priorityTone(priority: string): "info" | "warn" | "bad" {
  if (priority === "URGENT" || priority === "HIGH") return "bad";
  if (priority === "NORMAL") return "info";
  return "warn";
}

export function TicketsPage() {
  const [params, setParams] = useSearchParams();
  const tab = (params.get("status") ?? "ALL").toUpperCase();
  const priority = (params.get("priority") ?? "ALL").toUpperCase();
  const q = params.get("q") ?? "";
  const [draft, setDraft] = useState(q);

  const queue = useQuery({
    queryKey: ["support-queue", { tab, priority, q }],
    queryFn: () =>
      fetchQueue({
        status: tab === "ALL" ? undefined : tab,
        priority: priority === "ALL" ? undefined : priority,
        q: q || undefined,
      }),
  });

  function update(patch: Record<string, string>) {
    const next = new URLSearchParams(params);
    for (const [k, v] of Object.entries(patch)) {
      if (v && v !== "ALL") next.set(k, v);
      else next.delete(k);
    }
    setParams(next);
  }

  return (
    <div className="flex flex-col gap-4">
      <h1 className="sp-title">Ticket queue</h1>

      <div className="flex flex-wrap gap-1.5" role="tablist" aria-label="Filter by status">
        {STATUS_TABS.map((s) => (
          <button
            key={s}
            role="tab"
            aria-selected={tab === s}
            className={`sp-btn ${tab === s ? "sp-btn-primary" : "sp-btn-secondary"}`}
            style={{ padding: "0.375rem 0.75rem", fontSize: 13 }}
            onClick={() => update({ status: s })}
          >
            {s === "ALL" ? "All" : s.charAt(0) + s.slice(1).toLowerCase()}
          </button>
        ))}
      </div>

      <div className="flex flex-col gap-2 sm:flex-row">
        <form
          className="flex flex-1 gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            update({ q: draft.trim() });
          }}
        >
          <Input
            placeholder="Search ticket number or subject…"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            aria-label="Search tickets"
          />
          <Button type="submit" variant="secondary" aria-label="Search">
            <Search size={15} aria-hidden />
          </Button>
        </form>
        <select
          className="sp-input sm:w-40"
          value={priority}
          onChange={(e) => update({ priority: e.target.value })}
          aria-label="Filter by priority"
        >
          {PRIORITIES.map((p) => (
            <option key={p} value={p}>{p === "ALL" ? "All priorities" : p}</option>
          ))}
        </select>
      </div>

      {queue.isPending ? (
        <Card><p className="sp-muted">Loading queue…</p></Card>
      ) : queue.isError ? (
        <Card>
          <ErrorState title="Could not load queue" hint="Start the backend and try again." onRetry={() => void queue.refetch()} />
        </Card>
      ) : (queue.data ?? []).length === 0 ? (
        <Card>
          <EmptyState
            title="No tickets match"
            hint="Try a different status tab or clear the search."
            action={q || tab !== "ALL" || priority !== "ALL" ? (
              <Button variant="secondary" onClick={() => { setDraft(""); setParams({}); }}>
                Clear filters
              </Button>
            ) : undefined}
          />
        </Card>
      ) : (
        <Card className="!p-2">
          <ul className="flex flex-col">
            {(queue.data ?? []).map((t) => (
              <li key={t.id}>
                <Link
                  to={`/tickets/${t.id}`}
                  className="ns-row-between gap-3 rounded-lg px-3 py-2.5 hover:bg-slate-50"
                >
                  <span className="flex min-w-0 items-center gap-2.5">
                    <LifeBuoy size={15} aria-hidden className="shrink-0 text-slate-400" />
                    <span className="min-w-0">
                      <span className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-sm">
                        <span className="font-semibold">{t.ticket_number}</span>
                        <Badge tone={priorityTone(t.priority)}>{t.priority}</Badge>
                        <Badge tone={statusTone(t.status)}>{t.status}</Badge>
                      </span>
                      <span className="block truncate text-[13px] text-slate-600">
                        {t.subject} · {t.customer_name}
                        {t.order_number ? ` · ${t.order_number}` : ""} · {t.message_count} msg
                      </span>
                    </span>
                  </span>
                  <span className="sp-muted shrink-0 text-xs">{formatDate(t.created_at)}</span>
                </Link>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}

function ConsoleBubble({ m }: { m: ConsoleMessage }) {
  if (m.sender_type === "SYSTEM") {
    return <p className="sp-muted mx-auto max-w-[90%] text-center text-xs">— {m.message}</p>;
  }
  if (m.is_internal) {
    return (
      <div className="rounded-xl border border-dashed border-amber-300 bg-amber-50 px-3.5 py-2.5 text-sm">
        <p className="mb-0.5 flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wider text-amber-700">
          <StickyNote size={11} aria-hidden /> Internal note · staff only
        </p>
        <p className="whitespace-pre-wrap text-slate-800">{m.message}</p>
        <p className="mt-1 text-[11px] text-slate-400">{formatDate(m.created_at)}</p>
      </div>
    );
  }
  const staff = m.sender_type === "SUPPORT_AGENT";
  return (
    <div className={`flex ${staff ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-sm ${
          staff ? "rounded-br-md bg-indigo-600 text-white" : "rounded-bl-md bg-slate-100 text-slate-800"
        }`}
      >
        {!staff ? (
          <p className="mb-0.5 text-[11px] font-semibold uppercase tracking-wider opacity-70">
            {m.sender_type === "AI_AGENT" ? "AI assistant" : "Customer"}
          </p>
        ) : null}
        <p className="whitespace-pre-wrap">{m.message}</p>
        <p className={`mt-1 text-[11px] ${staff ? "text-indigo-200" : "text-slate-400"}`}>
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
  const detail = useQuery({ queryKey: ["support-ticket", id], queryFn: () => fetchTicketDetail(id) });
  const navQueue = useQuery({ queryKey: ["support-queue", "nav"], queryFn: () => fetchQueue({}) });

  const [reply, setReply] = useState("");
  const [note, setNote] = useState("");
  const [resolution, setResolution] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run(action: string, fn: () => Promise<unknown>) {
    setBusy(action);
    setError(null);
    try {
      await fn();
      setReply("");
      setNote("");
      await qc.invalidateQueries({ queryKey: ["support-ticket", id] });
      await qc.invalidateQueries({ queryKey: ["support-queue"] });
      await qc.invalidateQueries({ queryKey: ["support-stats"] });
    } catch (err) {
      setError(staffApiErrorMessage(err, "Action failed. Please try again."));
    } finally {
      setBusy(null);
    }
  }

  if (detail.isPending) {
    return <Card><p className="sp-muted">Loading ticket…</p></Card>;
  }
  if (detail.isError) {
    return (
      <Card>
        <ErrorState title="Ticket not found" hint="It may have been removed." onRetry={() => void detail.refetch()} />
      </Card>
    );
  }

  const t = detail.data;
  const actionable = t.status === "OPEN" || t.status === "ESCALATED";

  return (
    <div className="flex flex-col gap-3">
      <button className="sp-btn sp-btn-ghost self-start" style={{ padding: "0.25rem 0.5rem", fontSize: 13 }} onClick={() => nav("/tickets")}>
        <ArrowLeft size={14} aria-hidden /> Queue
      </button>

      <div className="grid items-start gap-4 xl:grid-cols-[220px_minmax(0,1fr)_300px]">
        <Card className="!p-3">
          <p className="sp-muted mb-2 text-xs font-semibold uppercase tracking-wider">Queue</p>
          <ul className="flex max-h-96 flex-col gap-1 overflow-y-auto">
            {(navQueue.data ?? []).map((q) => (
              <li key={q.id}>
                <Link
                  to={`/tickets/${q.id}`}
                  className={`block truncate rounded-md px-2 py-1.5 text-[13px] ${
                    q.id === id ? "bg-indigo-50 font-semibold text-indigo-800" : "hover:bg-slate-50"
                  }`}
                >
                  {q.ticket_number} · {q.status.toLowerCase()}
                </Link>
              </li>
            ))}
          </ul>
        </Card>

        <div className="flex min-w-0 flex-col gap-3">
          <Card>
            <div className="ns-row-between gap-2">
              <div className="min-w-0">
                <h1 className="sp-title">{t.ticket_number}</h1>
                <p className="sp-muted truncate">{t.subject} · {t.category.toLowerCase()} · {t.priority.toLowerCase()} priority</p>
              </div>
              <Badge tone={statusTone(t.status)}>{t.status}</Badge>
            </div>
            <p className="mt-2 rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-700">{t.description}</p>
          </Card>

          <Card>
            <div className="flex flex-col gap-2.5">
              {t.messages.map((m) => (
                <ConsoleBubble key={m.id} m={m} />
              ))}
            </div>

            {actionable ? (
              <div className="mt-4 flex flex-col gap-2 border-t border-slate-100 pt-3">
                <form
                  className="flex gap-2"
                  onSubmit={(e) => {
                    e.preventDefault();
                    if (reply.trim()) void run("reply", () => replyToTicket(id, reply.trim()));
                  }}
                >
                  <Input
                    placeholder="Reply to customer…"
                    value={reply}
                    onChange={(e) => setReply(e.target.value)}
                    aria-label="Reply to customer"
                  />
                  <Button type="submit" disabled={busy !== null || !reply.trim()} aria-label="Send reply">
                    <Send size={15} aria-hidden />
                  </Button>
                </form>
                <form
                  className="flex gap-2"
                  onSubmit={(e) => {
                    e.preventDefault();
                    if (note.trim()) void run("note", () => addInternalNote(id, note.trim()));
                  }}
                >
                  <Input
                    placeholder="Internal note (staff only)…"
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    aria-label="Add internal note"
                  />
                  <Button type="submit" variant="secondary" disabled={busy !== null || !note.trim()}>
                    Add note
                  </Button>
                </form>
                <div className="flex flex-col gap-2 sm:flex-row">
                  <Input
                    placeholder="Resolution summary…"
                    value={resolution}
                    onChange={(e) => setResolution(e.target.value)}
                    aria-label="Resolution summary"
                  />
                  <div className="flex gap-2">
                    <Button
                      disabled={busy !== null || resolution.trim().length < 5}
                      onClick={() => void run("resolve", () => resolveTicket(id, resolution.trim()))}
                    >
                      {busy === "resolve" ? "Resolving…" : "Resolve"}
                    </Button>
                    <Button
                      variant="secondary"
                      disabled={busy !== null}
                      onClick={() => void run("escalate", () => escalateTicket(id, undefined))}
                    >
                      {busy === "escalate" ? "Escalating…" : "Escalate"}
                    </Button>
                  </div>
                </div>
                <Button variant="ghost" disabled title="AI solve arrives in Phase 8">
                  Solve with AI · Phase 8
                </Button>
              </div>
            ) : (
              <p className="sp-muted mt-4 border-t border-slate-100 pt-3 text-center">
                Ticket {t.status.toLowerCase()}.
                {t.resolution ? ` Resolution: ${t.resolution}` : ""}
              </p>
            )}
            {error ? <p className="mt-2 text-sm text-red-600" role="alert">{error}</p> : null}
          </Card>
        </div>

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
                  </li>
                ))}
              </ul>
              <p className="sp-muted mt-1.5 text-[13px]">
                {t.related_order.total_display} · {t.related_order.payment_status}
                {t.related_order.payment_reference ? ` · ${t.related_order.payment_reference}` : ""}
              </p>
              <p className="sp-muted mt-0.5 text-[13px]">{t.related_order.shipping_address}</p>
            </Card>
          ) : (
            <Card><p className="sp-muted text-[13px]">No linked order.</p></Card>
          )}

          {t.policies.length > 0 ? (
            <Card>
              <p className="sp-muted mb-1 text-xs font-semibold uppercase tracking-wider">Policies</p>
              <ul className="flex flex-col gap-1.5 text-[13px] text-slate-600">
                {t.policies.map((p) => (
                  <li key={p.product_name}>
                    <span className="font-medium text-slate-800">{p.product_name}:</span> {p.summary}
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
                    <span className="sp-muted"> · {p.status.toLowerCase()}</span>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
