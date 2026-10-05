import { motion, useReducedMotion } from "framer-motion";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ErrorState, LoadingState } from "@/shared/ui/feedback";
import { EmptyState } from "@/shared/ui/empty-state";
import { getErrorMessage } from "@/shared/lib/errors";
import { Badge } from "@/shared/ui/badge";
import { useTicketQueue, useUiFlags } from "../hooks/useTickets";
import type { TicketListResponse } from "../../types";

/** Deterministic visual-only priority from category (no backend field). */
function priorityFor(ticket: { category: string; status: string }): {
  label: string;
  cls: string;
} {
  if (ticket.status === "open" && ticket.category === "damage")
    return { label: "High", cls: "border-red-200 bg-red-50 text-red-800" };
  if (ticket.category === "refund")
    return { label: "Medium", cls: "border-amber-200 bg-amber-50 text-amber-800" };
  return { label: "Normal", cls: "border-slate-200 bg-slate-100 text-slate-600" };
}

/** Static SLA text derived from the ticket code (stable, no timers). */
function slaFor(code: string): string {
  let h = 0;
  for (let i = 0; i < code.length; i++) h = (h * 31 + code.charCodeAt(i)) % 12;
  return `SLA ${2 + h}h left`;
}

function initials(code: string): string {
  const letters = code.replace(/[^A-Za-z]/g, "");
  return (letters.slice(0, 2) || "TK").toUpperCase();
}

export function TicketQueue({ initialPage = 1 }: { initialPage?: number }) {
  const [page, setPage] = useState(initialPage);
  const queue = useTicketQueue(page);
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);
  const stale = useUiFlags().data?.stale_rerender === true;

  // STALE_ELEMENT fault surface: the queue subtree remounts every few
  // seconds (fresh DOM nodes, new timestamps), invalidating element refs.
  // The worker must re-observe instead of replaying stale handles.
  useEffect(() => {
    if (!stale) return;
    const timer = window.setInterval(() => {
      setUpdatedAt(new Date().toLocaleTimeString());
    }, 3000);
    return () => window.clearInterval(timer);
  }, [stale]);

  return (
    <>
      {stale && updatedAt && (
        <p className="mb-2 text-xs text-slate-500">Updated at {updatedAt}</p>
      )}
      <TicketQueueView key={updatedAt ?? "steady"} page={page} setPage={setPage} queue={queue} />
    </>
  );
}

// Split for testability: pure view over a queue result.
export function TicketQueueView({
  page,
  setPage,
  queue,
}: {
  page: number;
  setPage: (page: number) => void;
  queue: {
    isPending: boolean;
    isError: boolean;
    error: unknown;
    data?: TicketListResponse;
    refetch: () => void;
  };
}) {
  const reduce = useReducedMotion();
  const { ticketCode: activeCode } = useParams();
  if (queue.isPending) return <LoadingState what="tickets" />;
  if (queue.isError)
    return <ErrorState message={getErrorMessage(queue.error)} onRetry={() => queue.refetch()} />;
  const data = queue.data;
  if (!data) return <LoadingState what="tickets" />;
  if (data.items.length === 0)
    return <EmptyState title="Queue is empty" desc="No tickets match this view." />;
  const totalPages = Math.max(1, Math.ceil(data.total / data.page_size));
  return (
    <div>
      <div className="ns-table-wrap">
        <table className="ns-table">
          <thead>
            <tr>
              <th scope="col">Ticket</th>
              <th scope="col">Subject</th>
              <th scope="col">Status</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((ticket, i) => {
              const pri = priorityFor(ticket);
              const active = activeCode === ticket.code;
              return (
                <motion.tr
                  key={ticket.id}
                  initial={reduce ? false : { opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: reduce ? 0 : Math.min(i * 0.03, 0.3), duration: 0.25 }}
                  className={active ? "is-active" : undefined}
                >
                  <td className="relative whitespace-nowrap">
                    {active && (
                      <motion.span
                        layoutId="ticket-active-row"
                        aria-hidden
                        transition={reduce ? { duration: 0 } : { type: "spring", stiffness: 500, damping: 40 }}
                        className="absolute inset-y-1 left-1 w-1 rounded-full bg-indigo-600"
                      />
                    )}
                    <span className="flex items-center gap-2.5">
                      <span
                        aria-hidden
                        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-[11px] font-bold text-indigo-700"
                      >
                        {initials(ticket.code)}
                      </span>
                      <span>
                        <Link
                          to={`/ops/tickets/${ticket.code}`}
                          className="block font-mono text-[13px] font-medium text-indigo-700 hover:underline"
                        >
                          {ticket.code}
                        </Link>
                        <span className="block text-[11px] text-slate-400">{slaFor(ticket.code)}</span>
                      </span>
                    </span>
                  </td>
                  <td className="max-w-[420px]">
                    <span className="block truncate font-medium text-slate-900">
                      {ticket.subject}
                    </span>
                    <span className="mt-0.5 block text-xs text-slate-400">{ticket.category}</span>
                  </td>
                  <td className="whitespace-nowrap">
                    <span className="flex flex-wrap items-center gap-1.5">
                      <Badge tone={ticket.status}>{ticket.status.split("_").join(" ")}</Badge>
                      <span className={`ns-badge ${pri.cls}`}>{pri.label}</span>
                    </span>
                  </td>
                </motion.tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <nav
        aria-label="Ticket pages"
        className="mt-3 flex flex-wrap items-center gap-2 text-sm"
      >
        <button
          type="button"
          disabled={page <= 1}
          onClick={() => setPage(page - 1)}
          className="ns-btn ns-btn-secondary ns-btn-sm"
        >
          Previous
        </button>
        <span aria-live="polite" className="text-[13px] text-slate-500">
          Page {page} of {totalPages} · {data.total} tickets · 10 per page
        </span>
        <button
          type="button"
          disabled={page >= totalPages}
          onClick={() => setPage(page + 1)}
          className="ns-btn ns-btn-secondary ns-btn-sm"
        >
          Next
        </button>
      </nav>
    </div>
  );
}
