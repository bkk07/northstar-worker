import { Inbox } from "lucide-react";
import { TicketQueue } from "../components/TicketQueue";
import { PageHeader } from "@/shared/ui/page-header";
import { Card, CardBody, CardHeader } from "@/shared/ui/card";

export default function TicketQueuePage() {
  return (
    <main className="ns-page space-y-5">
      <PageHeader
        eyebrow="Ops console"
        title="Ticket queue"
        desc="Paginated at 10 per page by design — the worker must paginate like a human. Open a ticket for the full workspace: conversation, context and actions."
      />
      <Card lift={false}>
        <CardHeader
          title="Open work"
          desc="Avatar · priority · live SLA per row. Status comes from the source of truth."
          actions={
            <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
              <Inbox aria-hidden className="h-3.5 w-3.5" />
              Queue
            </span>
          }
        />
        <CardBody>
          <TicketQueue />
        </CardBody>
      </Card>
    </main>
  );
}
