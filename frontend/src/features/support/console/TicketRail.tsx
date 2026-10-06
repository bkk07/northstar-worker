import { Inbox, Plus, Search } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { useTicketQueue } from "@/features/ops/tickets/hooks/useTickets";
import { Badge } from "@/shared/ui/badge";
import { Card, CardBody, CardHeader } from "@/shared/ui/card";
import { EmptyState } from "@/shared/ui/empty-state";
import { Skeleton } from "@/shared/ui/skeleton";
import { cn } from "@/shared/lib/utils";

/**
 * Ticket queue rail: search, pick a ticket to inspect, or hand it to the
 * bot with one click. Raising a ticket opens the dialog (page-owned).
 */
export function TicketRail({
  selected,
  onSelect,
  onSolve,
  onRaise,
}: {
  selected: string | null;
  onSelect: (code: string) => void;
  onSolve: (code: string) => void;
  onRaise: () => void;
}) {
  const queue = useTicketQueue(1);
  const [filter, setFilter] = useState("");
  const items = (queue.data?.items ?? []).filter((ticket) => {
    const needle = filter.trim().toLowerCase();
    if (!needle) return true;
    return (
      ticket.code.toLowerCase().includes(needle) ||
      ticket.subject.toLowerCase().includes(needle) ||
      ticket.status.toLowerCase().includes(needle)
    );
  });

  return (
    <Card lift={false} className="flex min-h-0 flex-1 flex-col">
      <CardHeader
        title="Tickets"
        desc={queue.data ? `${queue.data.total} in queue` : "Queue"}
        actions={
          <button
            type="button"
            onClick={onRaise}
            aria-label="Raise a ticket"
            className="ns-btn ns-btn-primary ns-btn-sm"
          >
            <Plus aria-hidden className="h-4 w-4" />
            Raise
          </button>
        }
      />
      <CardBody className="flex min-h-0 flex-1 flex-col gap-3">
        <label className="relative block">
          <span className="sr-only">Search tickets</span>
          <Search
            aria-hidden
            className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
          />
          <input
            value={filter}
            onChange={(event) => setFilter(event.target.value)}
            placeholder="Search code, subject, status…"
            className="ns-input w-full pl-8"
          />
        </label>
        <div aria-label="Ticket queue" className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto pr-0.5">
          {queue.isPending &&
            [0, 1, 2].map((index) => <Skeleton key={index} className="h-16" />)}
          {queue.isError && (
            <EmptyState
              title="Queue unavailable"
              desc="The ticket list failed to load."
              action={
                <button
                  type="button"
                  onClick={() => queue.refetch()}
                  className="ns-btn ns-btn-secondary ns-btn-sm"
                >
                  Retry
                </button>
              }
            />
          )}
          {queue.data && items.length === 0 && (
            <EmptyState
              title="No tickets match"
              desc={filter ? "Try a different search." : "The queue is empty."}
              icon={Inbox}
            />
          )}
          {items.map((ticket) => {
            const active = ticket.code === selected;
            return (
              <div
                key={ticket.code}
                className={cn(
                  "rounded-xl border p-2.5 transition-colors",
                  active
                    ? "border-indigo-500 bg-indigo-50/70"
                    : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50",
                )}
              >
                <button
                  type="button"
                  onClick={() => onSelect(ticket.code)}
                  aria-pressed={active}
                  className="block w-full text-left"
                >
                  <span className="flex items-center justify-between gap-2">
                    <span className="text-[13px] font-semibold text-slate-900">{ticket.code}</span>
                    <Badge tone={ticket.status}>{ticket.status}</Badge>
                  </span>
                  <span className="mt-0.5 line-clamp-2 block text-[13px] leading-5 text-slate-600">
                    {ticket.subject}
                  </span>
                </button>
                <button
                  type="button"
                  onClick={() => onSolve(ticket.code)}
                  className="mt-1.5 text-[13px] font-medium text-indigo-700 hover:underline"
                >
                  Solve with bot →
                </button>
              </div>
            );
          })}
        </div>
        <Link to="/ops/tickets" className="text-[13px] font-medium text-slate-500 hover:text-slate-700">
          Open full queue →
        </Link>
      </CardBody>
    </Card>
  );
}
