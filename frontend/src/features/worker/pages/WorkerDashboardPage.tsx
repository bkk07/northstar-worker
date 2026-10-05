import { TerminalSquare } from "lucide-react";
import { ApprovalQueue, ClarificationQueue } from "../approvals/components/ApprovalQueue";
import { DashboardCards, QueueDonut } from "../dashboard/components/DashboardCards";
import { CreateTaskDialog } from "../tasks/components/CreateTaskDialog";
import { TaskList } from "../tasks/components/TaskList";
import { PageEnter, PageEnterItem, PageHeader, Section } from "@/shared/ui/page-header";
import { Card, CardBody, CardHeader } from "@/shared/ui/card";
import { useApprovals, useClarifications, useWorkerTasks } from "../hooks/useWorker";

function QueueDonutPanel() {
  const approvals = useApprovals();
  const clarifications = useClarifications();
  const tasks = useWorkerTasks();
  const a = (approvals.data ?? []).length;
  const c = (clarifications.data ?? []).length;
  const t = (tasks.data ?? []).length;
  return <QueueDonut approvals={a} clarifications={c} tasks={t} />;
}

export default function WorkerDashboardPage() {
  return (
    <main className="ns-page space-y-6">
      <PageHeader
        eyebrow="Control center"
        title="Worker Control Center"
        desc="Submit work with the command bar, watch it fly into the queue, clear approvals with a swipe, and inspect proof."
      />

      {/* Command bar */}
      <PageEnter>
        <PageEnterItem>
          <Card lift={false} className="overflow-hidden">
            <div className="border-b border-slate-100 bg-slate-950 px-4 py-2.5 sm:px-5">
              <p className="flex items-center gap-2 text-xs font-medium text-slate-400">
                <TerminalSquare aria-hidden className="h-3.5 w-3.5 text-indigo-400" />
                New task — ⌘↵ to send, contract compiles before any mutation
              </p>
            </div>
            <CardBody>
              <CreateTaskDialog />
            </CardBody>
          </Card>
        </PageEnterItem>
      </PageEnter>

      <div className="grid gap-6 lg:grid-cols-5">
        <div className="space-y-6 lg:col-span-3">
          <Section
            title="System health"
            desc="Backend, database and queue depth with live pulse. Red means fix the environment first."
          >
            <DashboardCards />
          </Section>
          <Section
            title="Tasks"
            desc="Newest first — fresh runs fly in at the top. Open one for timeline, policy, memory and evidence."
          >
            <TaskList />
          </Section>
        </div>

        <div className="space-y-6 lg:col-span-2">
          <Card lift={false}>
            <CardHeader title="Queue mix" desc="Where operator attention sits right now." />
            <CardBody>
              <QueueDonutPanel />
            </CardBody>
          </Card>
          <Card lift={false}>
            <CardHeader
              title="Needs an operator"
              desc="Swipe right to approve, left to reject. Clarifications re-enter the contract."
            />
            <CardBody className="space-y-4">
              <div>
                <h3 className="mb-2 text-[13px] font-semibold uppercase tracking-wider text-slate-500">
                  Approvals
                </h3>
                <ApprovalQueue />
              </div>
              <div>
                <h3 className="mb-2 text-[13px] font-semibold uppercase tracking-wider text-slate-500">
                  Clarifications
                </h3>
                <ClarificationQueue />
              </div>
            </CardBody>
          </Card>
        </div>
      </div>
    </main>
  );
}
