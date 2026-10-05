import { useParams } from "react-router-dom";
import { TicketStatusCard } from "../components/TicketStatusCard";
import { ErrorState, LoadingState } from "@/shared/ui/feedback";
import { PageEnter, PageEnterItem, PageHeader } from "@/shared/ui/page-header";
import { useTicket } from "../hooks/useShop";

export default function ShopTicketPage() {
  const { ticketCode } = useParams();
  const ticket = useTicket(ticketCode);

  return (
    <main className="ns-page-narrow space-y-5">
      <PageHeader
        eyebrow="Support"
        title="Ticket status"
        desc="Follow your request the way you follow a parcel — every step timestamped by the team."
      />
      {ticket.isPending && <LoadingState what="ticket" />}
      {ticket.isError && <ErrorState message="Could not load the ticket." />}
      {ticket.data && (
        <PageEnter>
          <PageEnterItem>
            <TicketStatusCard ticket={ticket.data} />
          </PageEnterItem>
        </PageEnter>
      )}
    </main>
  );
}
