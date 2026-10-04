import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ErrorState, LoadingState } from "@/shared/ui/feedback";
import { getErrorMessage } from "@/shared/lib/errors";
import { useTicketQueue, useUiFlags } from "../hooks/useTickets";
import type { TicketListResponse } from "../../types";

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
      {stale && updatedAt && <p className="text-xs text-slate-500">Updated at {updatedAt}</p>}
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
  if (queue.isPending) return <LoadingState what="tickets" />;
  if (queue.isError)
    return <ErrorState message={getErrorMessage(queue.error)} onRetry={() => queue.refetch()} />;
  const data = queue.data;
  if (!data) return <LoadingState what="tickets" />;
  const totalPages = Math.max(1, Math.ceil(data.total / data.page_size));
  return (
    <div>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-slate-500">
            <th>Ticket</th>
            <th>Subject</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {data.items.map((ticket) => (
            <tr key={ticket.id} className="border-t">
              <td>
                <Link to={`/ops/tickets/${ticket.code}`} className="underline">
                  {ticket.code}
                </Link>
              </td>
              <td>{ticket.subject}</td>
              <td>{ticket.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <nav aria-label="Ticket pages" className="mt-3 flex items-center gap-2 text-sm">
        <button
          type="button"
          disabled={page <= 1}
          onClick={() => setPage(page - 1)}
          className="rounded border px-2 py-1 disabled:opacity-50"
        >
          Previous
        </button>
        <span aria-live="polite">
          Page {page} of {totalPages} ({data.total} tickets)
        </span>
        <button
          type="button"
          disabled={page >= totalPages}
          onClick={() => setPage(page + 1)}
          className="rounded border px-2 py-1 disabled:opacity-50"
        >
          Next
        </button>
      </nav>
    </div>
  );
}
