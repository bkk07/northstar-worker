import type { TicketRead } from "../types";

const RESOLUTION: Record<string, string> = {
  open: "We have received your ticket and will look into it.",
  in_progress: "Our team is working on your ticket.",
  waiting_on_customer: "We need more information from you.",
  resolved: "Your ticket has been resolved.",
  closed: "This ticket is closed.",
};

export function TicketStatusCard({ ticket }: { ticket: TicketRead }) {
  return (
    <article aria-label={`Ticket ${ticket.code}`} className="rounded-md border p-4">
      <h2 className="font-semibold">{ticket.code}</h2>
      <p className="text-sm text-slate-600">{ticket.subject}</p>
      <dl className="mt-2 grid grid-cols-2 gap-1 text-sm">
        <dt className="text-slate-500">Status</dt>
        <dd>{ticket.status}</dd>
        <dt className="text-slate-500">Category</dt>
        <dd>{ticket.category}</dd>
      </dl>
      <p className="mt-2 text-sm">{RESOLUTION[ticket.status] ?? ticket.status}</p>
    </article>
  );
}
