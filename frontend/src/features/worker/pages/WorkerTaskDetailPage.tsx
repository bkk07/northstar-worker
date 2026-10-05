import { Link, useParams } from "react-router-dom";
import { ErrorState, LoadingState } from "@/shared/ui/feedback";
import { getErrorMessage } from "@/shared/lib/errors";
import { EvidenceViewer } from "../evidence/components/EvidenceViewer";
import { StatusBadge } from "../tasks/components/TaskList";
import { TaskTimeline } from "../timeline/components/TaskTimeline";
import { MemoryTable } from "../memory/components/MemoryTable";
import { useWorkerTask } from "../hooks/useWorker";

export default function WorkerTaskDetailPage() {
  const { taskId } = useParams();
  const task = useWorkerTask(taskId);
  if (task.isPending) return <LoadingState what="task" />;
  if (task.isError)
    return <ErrorState message={getErrorMessage(task.error)} onRetry={() => task.refetch()} />;
  if (!task.data) return <LoadingState what="task" />;
  return (
    <main className="mx-auto max-w-4xl p-8">
      <Link to="/worker" className="text-sm underline">
        ← Dashboard
      </Link>
      <h1 className="mt-2 text-xl font-semibold">{task.data.text}</h1>
      <p className="mt-1 flex items-center gap-2 text-sm text-slate-600">
        <StatusBadge status={task.data.status} />
        <span>{task.data.current_state}</span>
      </p>
      <section aria-label="Timeline" className="mt-6">
        <h2 className="text-lg font-medium">Timeline</h2>
        <div className="mt-2">
          <TaskTimeline taskId={task.data.id} />
        </div>
      </section>
      <section aria-label="Evidence" className="mt-6">
        <h2 className="text-lg font-medium">Evidence</h2>
        <div className="mt-2">
          <EvidenceViewer taskId={task.data.id} />
        </div>
      </section>
      <section aria-label="Memory" className="mt-6">
        <h2 className="text-lg font-medium">Memory</h2>
        <div className="mt-2">
          <MemoryTable taskId={task.data.id} />
        </div>
      </section>
    </main>
  );
}
