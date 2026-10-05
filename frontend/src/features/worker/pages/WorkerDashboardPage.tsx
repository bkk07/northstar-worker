import { ApprovalQueue, ClarificationQueue } from "../approvals/components/ApprovalQueue";
import { DashboardCards, QueueSummary } from "../dashboard/components/DashboardCards";
import { CreateTaskDialog } from "../tasks/components/CreateTaskDialog";
import { TaskList } from "../tasks/components/TaskList";

export default function WorkerDashboardPage() {
  return (
    <main className="mx-auto max-w-4xl p-8">
      <h1 className="text-2xl font-semibold">Worker Control Center</h1>
      <div className="mt-4">
        <DashboardCards />
      </div>
      <section aria-label="Submit a task" className="mt-6">
        <CreateTaskDialog />
      </section>
      <section aria-label="Tasks" className="mt-6">
        <h2 className="text-lg font-medium">Tasks</h2>
        <div className="mt-2">
          <TaskList />
        </div>
      </section>
      <section aria-label="Human in the loop" className="mt-6">
        <h2 className="text-lg font-medium">Waiting for an operator</h2>
        <div className="mt-2">
          <QueueSummary />
        </div>
        <h3 className="mt-4 font-medium">Approvals</h3>
        <div className="mt-2">
          <ApprovalQueue />
        </div>
        <h3 className="mt-4 font-medium">Clarifications</h3>
        <div className="mt-2">
          <ClarificationQueue />
        </div>
      </section>
    </main>
  );
}
