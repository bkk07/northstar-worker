import { useParams } from "react-router-dom";
import { ErrorState, LoadingState } from "@/shared/ui/feedback";
import { getErrorMessage } from "@/shared/lib/errors";
import { NoteForm, ReplyForm, StatusControl } from "../../notes/components/NoteForms";
import { RefundForm } from "../../refunds/components/RefundForm";
import { ReplacementForm } from "../../replacements/components/ReplacementForm";
import { useTicketDetail } from "../hooks/useTickets";

export default function TicketDetailPage() {
  const { ticketCode } = useParams();
  const detail = useTicketDetail(ticketCode);
  const refresh = () => detail.refetch();

  if (detail.isPending) return <LoadingState what="ticket" />;
  if (detail.isError || !detail.data)
    return (
      <main className="mx-auto max-w-3xl p-8">
        <ErrorState message={getErrorMessage(detail.error)} />
      </main>
    );
  const ticket = detail.data;

  return (
    <main className="mx-auto max-w-3xl space-y-6 p-8">
      <div>
        <h1 className="text-2xl font-semibold">{ticket.code}</h1>
        <p className="text-sm text-slate-600">
          {ticket.subject} · {ticket.status} · {ticket.category}
        </p>
        <p className="mt-2 text-sm">{ticket.body}</p>
      </div>
      <section aria-label="Mutations" className="grid gap-6 md:grid-cols-2">
        <ReplacementForm ticketCode={ticket.code} onCreated={refresh} />
        <RefundForm ticketCode={ticket.code} onCreated={refresh} />
        <NoteForm ticketCode={ticket.code} />
        <ReplyForm ticketCode={ticket.code} />
        <StatusControl ticketCode={ticket.code} current={ticket.status} />
      </section>
    </main>
  );
}
