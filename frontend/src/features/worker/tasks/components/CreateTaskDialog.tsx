import { useState } from "react";
import { getErrorMessage } from "@/shared/lib/errors";
import { useCreateTask } from "../../hooks/useWorker";

export function CreateTaskDialog({ onCreated }: { onCreated?: (taskId: string) => void }) {
  const [text, setText] = useState("");
  const created = useCreateTask();

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!text.trim()) return;
    const task = await created.mutateAsync(text.trim());
    setText("");
    onCreated?.(task.id);
  }

  return (
    <form aria-label="Create task" onSubmit={submit} className="flex flex-col gap-2">
      <label htmlFor="worker-task-text" className="text-sm font-medium">
        New task
      </label>
      <textarea
        id="worker-task-text"
        value={text}
        onChange={(event) => setText(event.target.value)}
        placeholder="Replace the damaged ProBook (ORD-1942, TCK-101)."
        rows={3}
        className="rounded border px-2 py-1 text-sm"
      />
      <div>
        <button
          type="submit"
          disabled={created.isPending || !text.trim()}
          className="rounded bg-slate-900 px-3 py-1 text-sm text-white disabled:opacity-50"
        >
          {created.isPending ? "Submitting…" : "Submit task"}
        </button>
      </div>
      {created.isError && (
        <p role="alert" className="text-sm text-red-700">
          {getErrorMessage(created.error)}
        </p>
      )}
      {created.isSuccess && <p className="text-sm text-green-700">Task submitted for execution.</p>}
    </form>
  );
}
