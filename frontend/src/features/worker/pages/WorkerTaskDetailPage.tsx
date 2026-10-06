import { Link, useParams } from "react-router-dom";
import { ErrorState, LoadingState } from "@/shared/ui/feedback";
import { getErrorMessage } from "@/shared/lib/errors";
import { EvidenceViewer } from "../evidence/components/EvidenceViewer";
import { TaskChat } from "../chat/components/TaskChat";
import { StatusBadge } from "../tasks/components/TaskList";
import { TaskTimeline } from "../timeline/components/TaskTimeline";
import { MemoryTable } from "../memory/components/MemoryTable";
import { PageHeader } from "@/shared/ui/page-header";
import { Card, CardBody, CardHeader } from "@/shared/ui/card";
import { useWorkerTask } from "../hooks/useWorker";

export default function WorkerTaskDetailPage() {
  const { taskId } = useParams();
  const task = useWorkerTask(taskId);
  if (task.isPending)
    return (
      <main className="ns-page">
        <LoadingState what="task" />
      </main>
    );
  if (task.isError)
    return (
      <main className="ns-page">
        <ErrorState message={getErrorMessage(task.error)} onRetry={() => task.refetch()} />
      </main>
    );
  if (!task.data)
    return (
      <main className="ns-page">
        <LoadingState what="task" />
      </main>
    );
  return (
    <main className="ns-page space-y-6">
      <Link
        to="/worker"
        className="inline-flex items-center gap-1 text-[13px] font-medium text-slate-500 hover:text-slate-900"
      >
        ← Back to dashboard
      </Link>
      <PageHeader
        eyebrow={`Task ${task.data.id.slice(0, 8)} · ${task.data.current_state}`}
        title={task.data.text}
        desc={`Created ${new Date(task.data.created_at).toLocaleString()} — contract → plan → policy → execute → verify. Everything below is read from the audit journal.`}
        actions={<StatusBadge status={task.data.status} />}
      />
      <div className="grid gap-6 lg:grid-cols-5">
        <div className="lg:col-span-5">
          <TaskChat task={task.data} />
        </div>
        <Card className="lg:col-span-3">
          <CardHeader
            title="Live timeline"
            desc="Node transitions, tool calls, failures and recoveries in order."
          />
          <CardBody>
            <TaskTimeline taskId={task.data.id} />
          </CardBody>
        </Card>
        <div className="space-y-6 lg:col-span-2">
          <Card>
            <CardHeader title="Evidence" desc="Verifier-derived proof, not model text." />
            <CardBody>
              <EvidenceViewer taskId={task.data.id} />
            </CardBody>
          </Card>
          <Card>
            <CardHeader title="Memory" desc="Facts with provenance and trust level." />
            <CardBody>
              <MemoryTable taskId={task.data.id} />
            </CardBody>
          </Card>
        </div>
      </div>
    </main>
  );
}
