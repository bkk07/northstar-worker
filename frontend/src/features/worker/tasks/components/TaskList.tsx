import { Link } from "react-router-dom";
import { ErrorState, LoadingState } from "@/shared/ui/feedback";
import { getErrorMessage } from "@/shared/lib/errors";
import { useWorkerTasks } from "../../hooks/useWorker";
import type { TaskRead } from "../../types";

const STATUS_STYLES: Record<string, string> = {
  pending: "bg-slate-200 text-slate-700",
  running: "bg-blue-100 text-blue-800",
  waiting_for_approval: "bg-amber-100 text-amber-800",
  waiting_for_clarification: "bg-amber-100 text-amber-800",
  waiting_on_customer: "bg-amber-100 text-amber-800",
  succeeded: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
  blocked: "bg-red-100 text-red-800",
  inconclusive: "bg-purple-100 text-purple-800",
};

export function StatusBadge({ status }: { status: string }) {
  const style = STATUS_STYLES[status] ?? "bg-slate-100 text-slate-600";
  return <span className={`rounded px-2 py-0.5 text-xs font-medium ${style}`}>{status}</span>;
}

export function TaskList({ taskStatus }: { taskStatus?: string }) {
  const tasks = useWorkerTasks(taskStatus);
  if (tasks.isPending) return <LoadingState what="worker tasks" />;
  if (tasks.isError)
    return <ErrorState message={getErrorMessage(tasks.error)} onRetry={() => tasks.refetch()} />;
  return <TaskListView tasks={tasks.data ?? []} />;
}

// Split for testability: pure view over the task rows.
export function TaskListView({ tasks }: { tasks: TaskRead[] }) {
  if (tasks.length === 0) return <p className="text-sm text-slate-500">No tasks yet.</p>;
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left text-slate-500">
          <th>Task</th>
          <th>Status</th>
          <th>Created</th>
        </tr>
      </thead>
      <tbody>
        {tasks.map((task) => (
          <tr key={task.id} className="border-t">
            <td>
              <Link to={`/worker/tasks/${task.id}`} className="underline">
                {task.text.length > 80 ? `${task.text.slice(0, 80)}…` : task.text}
              </Link>
            </td>
            <td>
              <StatusBadge status={task.status} />
            </td>
            <td className="text-slate-500">{new Date(task.created_at).toLocaleString()}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
