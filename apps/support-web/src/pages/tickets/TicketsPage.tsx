import { Link, useParams } from "react-router-dom";
import { Card, Badge, EmptyState, Button } from "@/components/ui";

// Phase 1 ticket shell: 3-column layout placeholder. Manual actions Phase 6, AI Phase 8+.
export function TicketsPage() {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h1 className="sp-title">Ticket queue</h1>
        <Badge>Phase 6</Badge>
      </div>
      <Card>
        <EmptyState
          title="Queue is empty"
          hint="Search + status tabs (Open / Waiting / Escalated / Resolved) arrive in Phase 6."
          action={
            <Link to="/tickets/TKT-1024" className="sp-btn sp-btn-secondary">
              Preview ticket shell
            </Link>
          }
        />
      </Card>
    </div>
  );
}

export function TicketDetailPage() {
  const { id } = useParams();
  return (
    <div className="grid gap-4 lg:grid-cols-[220px_1fr_300px]">
      <Card>
        <p className="sp-muted">Queue nav</p>
        <p className="sp-title mt-1">{id}</p>
        <p className="sp-muted mt-2">Inbox / Open / Waiting / Escalated / Resolved (Phase 6).</p>
      </Card>
      <Card>
        <Badge>Conversation</Badge>
        <p className="sp-title mt-2">Ticket {id}</p>
        <p className="sp-muted">Customer messages, replies, internal notes, resolve/escalate (Phase 6).</p>
        <div className="mt-3 flex gap-2">
          <Button variant="secondary" disabled>Reply (Phase 6)</Button>
          <Button disabled>Solve with AI (Phase 8)</Button>
        </div>
      </Card>
      <Card>
        <Badge>Context</Badge>
        <p className="sp-title mt-2">Customer + Order</p>
        <p className="sp-muted">Profile, orders, product, payment, policy panel (Phase 6).</p>
      </Card>
    </div>
  );
}
