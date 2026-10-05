import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { CheckCircle2, CornerDownLeft, Sparkles } from "lucide-react";
import { useState } from "react";
import { getErrorMessage } from "@/shared/lib/errors";
import { useCreateTask } from "../../hooks/useWorker";
import { cn } from "@/shared/lib/utils";

const EXAMPLES = [
  "Replace the damaged ProBook (ORD-1942, TCK-101).",
  "Refund ₹2,500 to C102 for the late delivery.",
  "Add an internal note to TCK-104 and set it to in-progress.",
];

/**
 * Linear-style command bar: big input, example chips, animated submit.
 * The new task flies into the list via TaskList's layout animations
 * (create invalidates ["worker","tasks"]).
 */
export function CreateTaskDialog({ onCreated }: { onCreated?: (taskId: string) => void }) {
  const [text, setText] = useState("");
  const [justSent, setJustSent] = useState(false);
  const created = useCreateTask();
  const reduce = useReducedMotion();

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!text.trim() || created.isPending) return;
    try {
      const task = await created.mutateAsync(text.trim());
      setText("");
      setJustSent(true);
      window.setTimeout(() => setJustSent(false), 4000);
      onCreated?.(task.id);
    } catch {
      // created.isError renders below.
    }
  }

  return (
    <form aria-label="Create task" onSubmit={submit}>
      <div
        className={cn(
          "rounded-2xl border bg-white shadow-sm transition-colors focus-within:border-indigo-400 focus-within:ring-2 focus-within:ring-indigo-100",
          created.isError ? "border-red-300" : "border-slate-300",
        )}
      >
        <label htmlFor="worker-task-text" className="sr-only">
          New task
        </label>
        <div className="flex items-start gap-2.5 px-4 pt-3.5">
          <Sparkles aria-hidden className="mt-1 h-4 w-4 shrink-0 text-indigo-500" />
          <textarea
            id="worker-task-text"
            value={text}
            onChange={(event) => setText(event.target.value)}
            onKeyDown={(event) => {
              if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
                event.currentTarget.form?.requestSubmit();
              }
            }}
            placeholder="Tell the worker what to do… e.g. Replace the damaged ProBook (ORD-1942, TCK-101)."
            rows={3}
            className="w-full resize-y bg-transparent text-[15px] leading-6 text-slate-900 placeholder:text-slate-400 focus:outline-none"
          />
        </div>
        <div className="flex items-center gap-2 px-3.5 pb-3 pt-2">
          <span className="hidden text-[11px] text-slate-400 sm:block">⌘↵ to send</span>
          <span className="flex-1" />
          <AnimatePresence mode="wait" initial={false}>
            {justSent && created.isSuccess ? (
              <motion.span
                key="sent"
                role="status"
                initial={reduce ? false : { scale: 0.6, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ type: "spring", stiffness: 500, damping: 24 }}
                className="inline-flex items-center gap-1.5 text-[13px] font-medium text-emerald-700"
              >
                <CheckCircle2 aria-hidden className="h-4 w-4" />
                Task submitted for execution.
              </motion.span>
            ) : null}
          </AnimatePresence>
          <motion.button
            type="submit"
            disabled={created.isPending || !text.trim()}
            whileTap={reduce ? undefined : { scale: 0.97 }}
            className="ns-btn ns-btn-primary"
          >
            {created.isPending ? (
              <span className="inline-flex items-center gap-1.5">
                <span aria-hidden className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                Submitting…
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5">
                Submit task
                <CornerDownLeft aria-hidden className="h-3.5 w-3.5 opacity-70" />
              </span>
            )}
          </motion.button>
        </div>
      </div>

      <div className="mt-2.5 flex flex-wrap gap-1.5">
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            type="button"
            onClick={() => setText(ex)}
            className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-xs text-slate-600 shadow-sm transition-colors hover:border-indigo-300 hover:bg-indigo-50/50 hover:text-indigo-800"
          >
            Try: {ex.length > 44 ? `${ex.slice(0, 44)}…` : ex}
          </button>
        ))}
      </div>

      {created.isError && (
        <p role="alert" className="mt-2 text-sm text-red-700">
          {getErrorMessage(created.error)}
        </p>
      )}
      <p className="mt-2 text-xs text-slate-500">
        Free-form is fine — the worker compiles a contract first and asks when ambiguous.
      </p>
    </form>
  );
}
