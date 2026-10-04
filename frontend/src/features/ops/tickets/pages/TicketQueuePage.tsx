import { TicketQueue } from "../components/TicketQueue";

export default function TicketQueuePage() {
  return (
    <main className="mx-auto max-w-3xl p-8">
      <h1 className="text-2xl font-semibold">Ticket queue</h1>
      <div className="mt-4">
        <TicketQueue />
      </div>
    </main>
  );
}
