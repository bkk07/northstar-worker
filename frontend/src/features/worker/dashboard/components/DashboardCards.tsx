import { ErrorState, LoadingState } from "@/shared/ui/feedback";
import { getErrorMessage } from "@/shared/lib/errors";
import {
  useApprovals,
  useClarifications,
  useEnvironmentStatus,
  useWorkerTasks,
} from "../../hooks/useWorker";
import type { EnvironmentStatus } from "../../types";

export function DashboardCards() {
  const status = useEnvironmentStatus();
  const tasks = useWorkerTasks();
  if (status.isPending || tasks.isPending) return <LoadingState what="dashboard" />;
  if (status.isError)
    return <ErrorState message={getErrorMessage(status.error)} onRetry={() => status.refetch()} />;
  if (!status.data) return <LoadingState what="dashboard" />;
  return <DashboardCardsView status={status.data} taskCount={(tasks.data ?? []).length} />;
}

// Split for testability: pure view over status + counts.
export function DashboardCardsView({
  status,
  taskCount,
}: {
  status: EnvironmentStatus;
  taskCount: number;
}) {
  const cards: Array<[string, string]> = [
    ["Backend", status.backend],
    ["Database", status.database],
    ["Tasks (latest 50)", String(taskCount)],
    ["Pending tasks", String(status.pending_tasks)],
    ["Approvals waiting", String(status.pending_approvals)],
    ["Questions waiting", String(status.pending_clarifications)],
  ];
  return (
    <ul className="grid grid-cols-2 gap-3 md:grid-cols-3">
      {cards.map(([label, value]) => (
        <li key={label} className="rounded border p-3">
          <p className="text-xs text-slate-500">{label}</p>
          <p className="text-xl font-semibold">{value}</p>
        </li>
      ))}
    </ul>
  );
}

export function QueueSummary() {
  const approvals = useApprovals();
  const clarifications = useClarifications();
  const waiting = (approvals.data ?? []).length + (clarifications.data ?? []).length;
  if (approvals.isPending || clarifications.isPending) return <LoadingState what="queues" />;
  return (
    <p className="text-sm text-slate-600">
      {waiting} item{waiting === 1 ? "" : "s"} waiting for an operator.
    </p>
  );
}
