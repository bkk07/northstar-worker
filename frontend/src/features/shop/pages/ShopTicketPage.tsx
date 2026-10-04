import { useParams } from "react-router-dom";
import { TicketStatusCard } from "../components/TicketStatusCard";
import { ErrorState, LoadingState } from "../components/Feedback";
import { useTicket } from "../hooks/useShop";

export default function ShopTicketPage() {
  const { ticketCode } = useParams();
  const ticket = useTicket(ticketCode);

  return (
    <main className="mx-auto max-w-3xl p-8">
      <h1 className="text-2xl font-semibold">Ticket status</h1>
      <div className="mt-4">
        {ticket.isPending && <LoadingState what="ticket" />}
        {ticket.isError && <ErrorState message="Could not load the ticket." />}
        {ticket.data && <TicketStatusCard ticket={ticket.data} />}
      </div>
    </main>
  );
}
