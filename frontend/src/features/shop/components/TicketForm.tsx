import { useState } from "react";
import { useCreateTicket } from "../hooks/useShop";
import type { TicketFormState, TicketRead } from "../types";
import { ErrorState } from "@/shared/ui/feedback";

const EMPTY: TicketFormState = { subject: "", body: "", category: "damage" };

export function TicketForm({
  customerCode,
  orderCode,
  onCreated,
}: {
  customerCode: string;
  orderCode?: string;
  onCreated: (ticket: TicketRead) => void;
}) {
  const [form, setForm] = useState<TicketFormState>(EMPTY);
  const createTicket = useCreateTicket();

  const set =
    (field: keyof TicketFormState) =>
    (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
      setForm((prev) => ({ ...prev, [field]: event.target.value }));

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    try {
      const ticket = await createTicket.mutateAsync({
        customer_code: customerCode,
        order_code: orderCode ?? null,
        ...form,
      });
      onCreated(ticket);
    } catch {
      // createTicket.isError renders the error state; nothing else to do.
    }
  }

  return (
    <form aria-label="Raise a ticket" onSubmit={handleSubmit} className="mt-4 space-y-3">
      <h2 className="font-semibold">Raise a ticket</h2>
      <div>
        <label htmlFor="ticket-subject" className="block text-sm">
          Subject
        </label>
        <input
          id="ticket-subject"
          value={form.subject}
          onChange={set("subject")}
          required
          className="w-full rounded border px-2 py-1"
        />
      </div>
      <div>
        <label htmlFor="ticket-body" className="block text-sm">
          What happened?
        </label>
        <textarea
          id="ticket-body"
          value={form.body}
          onChange={set("body")}
          required
          rows={4}
          className="w-full rounded border px-2 py-1"
        />
      </div>
      <div>
        <label htmlFor="ticket-category" className="block text-sm">
          Category
        </label>
        <select
          id="ticket-category"
          value={form.category}
          onChange={set("category")}
          className="rounded border px-2 py-1"
        >
          <option value="damage">Damage</option>
          <option value="refund">Refund</option>
          <option value="late_delivery">Late delivery</option>
          <option value="cancellation">Cancellation</option>
          <option value="general">General</option>
        </select>
      </div>
      {createTicket.isError && <ErrorState message="Could not raise the ticket." />}
      <button
        type="submit"
        disabled={createTicket.isPending}
        className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-50"
      >
        {createTicket.isPending ? "Raising…" : "Raise ticket"}
      </button>
    </form>
  );
}
