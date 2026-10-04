import { useState } from "react";
import { ErrorState } from "@/shared/ui/feedback";
import { useToast } from "@/shared/ui/toast";
import { getErrorMessage } from "@/shared/lib/errors";
import { useCreateNote, useCreateReply, useUpdateStatus } from "../hooks/useNotes";

export function NoteForm({ ticketCode }: { ticketCode: string }) {
  const [body, setBody] = useState("");
  const create = useCreateNote(ticketCode);
  const toast = useToast();

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    try {
      await create.mutateAsync({ kind: "internal", body, author: "ops-agent" });
      setBody("");
      toast.push("Internal note added.");
    } catch {
      // ErrorState renders below.
    }
  }

  return (
    <form aria-label="Add internal note" onSubmit={handleSubmit} className="space-y-2">
      <h3 className="font-semibold">Internal note</h3>
      <label htmlFor="note-body" className="sr-only">
        Note text
      </label>
      <textarea
        id="note-body"
        value={body}
        onChange={(e) => setBody(e.target.value)}
        required
        rows={3}
        className="w-full rounded border px-2 py-1"
      />
      {create.isError && <ErrorState message={getErrorMessage(create.error)} />}
      <button
        type="submit"
        disabled={create.isPending}
        className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-50"
      >
        Add note
      </button>
    </form>
  );
}

export function ReplyForm({ ticketCode }: { ticketCode: string }) {
  const [body, setBody] = useState("");
  const create = useCreateReply(ticketCode);
  const toast = useToast();

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    try {
      await create.mutateAsync({ body });
      setBody("");
      toast.push("Reply sent to the customer.");
    } catch {
      // ErrorState renders below.
    }
  }

  return (
    <form aria-label="Reply to customer" onSubmit={handleSubmit} className="space-y-2">
      <h3 className="font-semibold">Customer reply</h3>
      <label htmlFor="reply-body" className="sr-only">
        Reply text
      </label>
      <textarea
        id="reply-body"
        value={body}
        onChange={(e) => setBody(e.target.value)}
        required
        rows={3}
        className="w-full rounded border px-2 py-1"
      />
      {create.isError && <ErrorState message={getErrorMessage(create.error)} />}
      <button
        type="submit"
        disabled={create.isPending}
        className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-50"
      >
        Send reply
      </button>
    </form>
  );
}

const STATUSES = ["open", "in_progress", "waiting_on_customer", "resolved", "closed"];

export function StatusControl({ ticketCode, current }: { ticketCode: string; current: string }) {
  const [toStatus, setToStatus] = useState(current);
  const update = useUpdateStatus(ticketCode);
  const toast = useToast();

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    try {
      await update.mutateAsync({ to_status: toStatus });
      toast.push(`Ticket set to ${toStatus}.`);
    } catch {
      // ErrorState renders below.
    }
  }

  return (
    <form aria-label="Change ticket status" onSubmit={handleSubmit} className="space-y-2">
      <h3 className="font-semibold">Status</h3>
      <label htmlFor="status-select" className="sr-only">
        New status
      </label>
      <select
        id="status-select"
        value={toStatus}
        onChange={(e) => setToStatus(e.target.value)}
        className="rounded border px-2 py-1"
      >
        {STATUSES.map((status) => (
          <option key={status} value={status}>
            {status}
          </option>
        ))}
      </select>
      {update.isError && <ErrorState message={getErrorMessage(update.error)} />}
      <button
        type="submit"
        disabled={update.isPending}
        className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-50"
      >
        Change status
      </button>
    </form>
  );
}
