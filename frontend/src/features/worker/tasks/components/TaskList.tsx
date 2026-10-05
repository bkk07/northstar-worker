import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ArrowUpRight } from "lucide-react";
import { Link } from "react-router-dom";
import { ErrorState, LoadingState } from "@/shared/ui/feedback";
import { getErrorMessage } from "@/shared/lib/errors";
import { Badge } from "@/shared/ui/badge";
import { EmptyState } from "@/shared/ui/empty-state";
import { useWorkerTasks } from "../../hooks/useWorker";
import type { TaskRead } from "../../types";

export function StatusBadge({ status }: { status: string }) {
  const label = status.split("_").join(" ");
  return <Badge tone={status}>{label}</Badge>;
}

export function TaskList({ taskStatus }: { taskStatus?: string }) {
  const tasks = useWorkerTasks(taskStatus);
  if (tasks.isPending) return <LoadingState what="worker tasks" />;
  if (tasks.isError)
    return <ErrorState message={getErrorMessage(tasks.error)} onRetry={() => tasks.refetch()} />;
  return <TaskListView tasks={tasks.data ?? []} />;
}

// Split for testability: pure view over the task rows.
// New tasks fly in via layout + enter animations (reduced-motion safe).
export function TaskListView({ tasks }: { tasks: TaskRead[] }) {
  const reduce = useReducedMotion();
  if (tasks.length === 0)
    return (
      <EmptyState
        title="No tasks yet"
        desc="Submit your first task above — e.g. 'Replace the damaged item for ticket TCK-101'."
      />
    );
  return (
    <motion.ul layout={reduce ? undefined : "position"} className="space-y-2.5">
      <AnimatePresence initial={false}>
        {tasks.map((task) => (
          <motion.li
            key={task.id}
            layout={reduce ? undefined : "position"}
            initial={reduce ? false : { opacity: 0, y: -14, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={reduce ? undefined : { opacity: 0, scale: 0.97 }}
            transition={{ type: "spring", stiffness: 380, damping: 30 }}
          >
            <Link
              to={`/worker/tasks/${task.id}`}
              className="ns-card group flex items-center gap-3 !rounded-2xl px-4 py-3 transition-colors hover:border-indigo-300"
              title={task.text}
            >
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-medium text-slate-900 group-hover:text-indigo-800">
                  {task.text}
                </span>
                <span className="mt-0.5 block font-mono text-[11px] text-slate-400">
                  {task.id.slice(0, 8)} · {task.current_state} ·{" "}
                  {new Date(task.created_at).toLocaleString()}
                </span>
              </span>
              <StatusBadge status={task.status} />
              <ArrowUpRight
                aria-hidden
                className="h-4 w-4 shrink-0 text-slate-300 transition-colors group-hover:text-indigo-500"
              />
            </Link>
          </motion.li>
        ))}
      </AnimatePresence>
    </motion.ul>
  );
}
