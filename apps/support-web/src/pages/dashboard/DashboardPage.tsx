import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Inbox, LifeBuoy } from "lucide-react";
import { Badge, Card, EmptyState, ErrorState } from "@/components/ui";
import { fetchApprovals, fetchQueue, fetchStats } from "@/services/support-api";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("en-IN", {
    day: "numeric",
    month: "short",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function DashboardPage() {
  const stats = useQuery({ queryKey: ["support-stats"], queryFn: fetchStats });
  const openQueue = useQuery({
    queryKey: ["support-queue", "open-preview"],
    queryFn: () => fetchQueue({ status: "OPEN" }),
  });
  const approvals = useQuery({
    queryKey: ["support-approvals", "preview"],
    queryFn: () => fetchApprovals("PENDING"),
  });

  const cards = [
    { label: "Open", value: stats.data?.summary.open },
    { label: "In progress", value: stats.data?.summary.in_progress },
    { label: "Waiting", value: stats.data?.summary.waiting },
    { label: "Resolved", value: stats.data?.summary.resolved },
  ];

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="sp-title">Dashboard</h1>
        <Link to="/tickets" className="sp-btn sp-btn-secondary" style={{ padding: "0.375rem 0.75rem", fontSize: 13 }}>
          <Inbox size={14} aria-hidden /> Open queue
        </Link>
      </div>

      {stats.isError ? (
        <Card>
          <ErrorState
            title="Could not load stats"
            hint="Start the backend and try again."
            onRetry={() => void stats.refetch()}
          />
        </Card>
      ) : (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {cards.map((c) => (
            <Card key={c.label}>
              <p className="sp-muted">{c.label}</p>
              <p className="text-2xl font-bold">{stats.isPending ? "—" : c.value}</p>
            </Card>
          ))}
        </div>
      )}

      {(approvals.data ?? []).length > 0 ? (
        <Card>
          <div className="ns-row-between mb-2">
            <h2 className="sp-title" style={{ fontSize: 15 }}>
              Approvals awaiting you ({(approvals.data ?? []).length})
            </h2>
          </div>
          <ul className="flex flex-col gap-2">
            {(approvals.data ?? []).slice(0, 5).map((a) => (
              <li key={a.id}>
                <Link to={`/tickets/${a.ticket_id}`} className="ns-row-between rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 hover:bg-amber-100">
                  <span className="text-sm">
                    <span className="font-semibold">{a.action_type}</span>
                    <span className="sp-muted"> · {a.ticket_number}</span>
                  </span>
                  <Badge tone="warn">PENDING</Badge>
                </Link>
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      <Card>
        <div className="ns-row-between mb-2">
          <h2 className="sp-title" style={{ fontSize: 15 }}>Needs attention</h2>
          <Link to="/tickets?status=OPEN" className="text-[13px] font-medium text-indigo-700 hover:underline">
            View all open
          </Link>
        </div>
        {openQueue.isPending ? (
          <p className="sp-muted">Loading open tickets…</p>
        ) : openQueue.isError ? (
          <p className="sp-muted">Queue unavailable offline.</p>
        ) : (openQueue.data ?? []).length === 0 ? (
          <EmptyState
            title="Inbox zero"
            hint="No open tickets. New customer tickets will land here."
          />
        ) : (
          <ul className="flex flex-col gap-2">
            {(openQueue.data ?? []).slice(0, 5).map((t) => (
              <li key={t.id}>
                <Link to={`/tickets/${t.id}`} className="ns-row-between rounded-lg border border-slate-100 px-3 py-2 hover:bg-slate-50">
                  <span className="flex items-center gap-2 text-sm">
                    <LifeBuoy size={14} aria-hidden className="text-slate-400" />
                    <span className="font-semibold">{t.ticket_number}</span>
                    <span className="truncate text-slate-600">{t.subject}</span>
                  </span>
                  <span className="flex items-center gap-2">
                    <Badge tone={t.priority === "URGENT" || t.priority === "HIGH" ? "bad" : "info"}>
                      {t.priority}
                    </Badge>
                    <span className="sp-muted text-xs">{formatDate(t.created_at)}</span>
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
