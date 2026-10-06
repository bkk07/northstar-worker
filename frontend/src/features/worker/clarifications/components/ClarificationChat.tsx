import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Bot, CornerDownLeft, UserRound } from "lucide-react";
import { useState } from "react";
import { ErrorState } from "@/shared/ui/feedback";
import { getErrorMessage } from "@/shared/lib/errors";
import { Card, CardBody, CardHeader } from "@/shared/ui/card";
import { useAnswerClarification, useClarifications } from "../../hooks/useWorker";
import type { ClarificationRead } from "../../types";
import { cn } from "@/shared/lib/utils";

// Demo quick-fills: they fill the reply box, never send. The operator's
// explicit send is what enters memory with `operator` provenance.
const QUICK_FILLS = [
  "Replace the damaged item on its order.",
  "Refund the amount stated on the ticket.",
  "Add an internal note and set it to in-progress.",
];

/**
 * Chat-style clarification thread for one task. The agent's question reads
 * as a message, the operator answers inline, and the answered thread stays
 * visible as history. Renders nothing when the task has no clarifications.
 */
export function ClarificationChat({
  taskId,
  taskStatus,
  bare = false,
}: {
  taskId: string;
  taskStatus: string;
  bare?: boolean;
}) {
  const clarifications = useClarifications();
  if (clarifications.isPending) return null;
  if (clarifications.isError)
    return (
      <ErrorState
        message={getErrorMessage(clarifications.error)}
        onRetry={() => clarifications.refetch()}
      />
    );
  const items = (clarifications.data ?? []).filter((item) => item.task_id === taskId);
  if (items.length === 0) return null;
  return (
    <ClarificationChatView
      items={items}
      waiting={taskStatus === "waiting_for_clarification"}
      bare={bare}
    />
  );
}

// Split for testability: pure thread over one task's clarification items.
export function ClarificationChatView({
  items,
  waiting,
  bare = false,
}: {
  items: ClarificationRead[];
  waiting: boolean;
  bare?: boolean;
}) {
  const answered = useAnswerClarification();
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [sentIds, setSentIds] = useState<Record<string, boolean>>({});
  const openCount = items.filter((item) => item.answer == null).length;

  function send(itemId: string) {
    const answer = (drafts[itemId] ?? "").trim();
    if (!answer || answered.isPending) return;
    answered.mutate(
      { clarificationId: itemId, answer, answeredBy: "duty-ops" },
      { onSuccess: () => setSentIds((prev) => ({ ...prev, [itemId]: true })) },
    );
  }

  // Bare mode embeds just the thread (e.g. inside TaskChat) with no Card.
  if (bare)
    return (
      <>
        <ThreadBody
          items={items}
          drafts={drafts}
          setDrafts={setDrafts}
          sentIds={sentIds}
          send={send}
          sending={answered.isPending}
        />
        {answered.isError && (
          <p role="alert" className="mt-3 text-sm text-red-700">
            {getErrorMessage(answered.error)}
          </p>
        )}
      </>
    );

  return (
    <Card lift={false}>
      <CardHeader
        title="Conversation"
        desc="The agent asks, you answer — the run resumes from your answer."
        actions={
          waiting && openCount > 0 ? (
            <span
              role="status"
              className="inline-flex items-center gap-1.5 rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-800"
            >
              <span aria-hidden className="relative flex h-2 w-2">
                <span className="absolute h-full w-full animate-ping rounded-full bg-amber-400 opacity-60" />
                <span className="h-2 w-2 rounded-full bg-amber-500" />
              </span>
              Awaiting your answer
            </span>
          ) : (
            <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
              Resolved
            </span>
          )
        }
      />
      <CardBody>
        <ThreadBody
          items={items}
          drafts={drafts}
          setDrafts={setDrafts}
          sentIds={sentIds}
          send={send}
          sending={answered.isPending}
        />
        {answered.isError && (
          <p role="alert" className="mt-3 text-sm text-red-700">
            {getErrorMessage(answered.error)}
          </p>
        )}
      </CardBody>
    </Card>
  );
}

function ThreadBody({
  items,
  drafts,
  setDrafts,
  sentIds,
  send,
  sending,
}: {
  items: ClarificationRead[];
  drafts: Record<string, string>;
  setDrafts: (drafts: Record<string, string>) => void;
  sentIds: Record<string, boolean>;
  send: (itemId: string) => void;
  sending: boolean;
}) {
  const reduce = useReducedMotion();
  return (
    <div aria-label="Clarification thread" role="log" className="flex flex-col gap-3">
      <AnimatePresence initial={false}>
        {items.map((item) => {
          const open = item.answer == null;
          const justSent = sentIds[item.id] === true;
          return (
            <motion.div
              key={item.id}
              initial={reduce ? false : { opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25 }}
              className="flex flex-col gap-2"
            >
              {/* Agent question */}
              <div className="flex items-start gap-2.5">
                <span
                  aria-hidden
                  className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-white"
                >
                  <Bot className="h-4 w-4" />
                </span>
                <div className="max-w-[85%] rounded-2xl rounded-tl-md border border-indigo-100 bg-indigo-50/60 px-3.5 py-2.5">
                  <p className="flex flex-wrap items-center gap-2 text-[11px] font-semibold uppercase tracking-wide text-indigo-500">
                    Worker · {item.kind}
                    <span className="font-normal normal-case tracking-normal text-indigo-300">
                      {new Date(item.created_at).toLocaleString()}
                    </span>
                  </p>
                  <p className="mt-1 text-sm leading-6 text-slate-900">{item.question}</p>
                </div>
              </div>

              {/* Operator answer, once given */}
              {!open && (
                <div className="flex items-start justify-end gap-2.5">
                  <div className="max-w-[85%] rounded-2xl rounded-tr-md border border-emerald-100 bg-emerald-50 px-3.5 py-2.5">
                    <p className="flex items-center justify-end gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-emerald-600">
                      {item.answered_by ?? "Operator"}
                    </p>
                    <p className="mt-1 text-sm leading-6 text-slate-900">{item.answer}</p>
                  </div>
                  <span
                    aria-hidden
                    className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-emerald-600 text-white"
                  >
                    <UserRound className="h-4 w-4" />
                  </span>
                </div>
              )}

              {/* Reply box for open questions */}
              {open && (
                <form
                  aria-label={`Answer ${item.id}`}
                  className="ml-10 flex flex-col gap-2"
                  onSubmit={(event) => {
                    event.preventDefault();
                    send(item.id);
                  }}
                >
                  <div className="flex gap-2">
                    <label htmlFor={`chat-answer-${item.id}`} className="sr-only">
                      Answer
                    </label>
                    <input
                      id={`chat-answer-${item.id}`}
                      value={drafts[item.id] ?? ""}
                      onChange={(event) =>
                        setDrafts({ ...drafts, [item.id]: event.target.value })
                      }
                      placeholder="Type your answer — the run resumes from it…"
                      autoComplete="off"
                      className="ns-input flex-1"
                    />
                    <motion.button
                      type="submit"
                      disabled={sending || !(drafts[item.id] ?? "").trim()}
                      whileTap={reduce ? undefined : { scale: 0.97 }}
                      className="ns-btn ns-btn-primary ns-btn-sm shrink-0"
                    >
                      {sending ? (
                        "Sending…"
                      ) : (
                        <span className="inline-flex items-center gap-1.5">
                          Send
                          <CornerDownLeft aria-hidden className="h-3.5 w-3.5 opacity-70" />
                        </span>
                      )}
                    </motion.button>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {QUICK_FILLS.map((fill) => (
                      <button
                        key={fill}
                        type="button"
                        onClick={() => setDrafts({ ...drafts, [item.id]: fill })}
                        className={cn(
                          "rounded-full border border-slate-200 bg-white px-2.5 py-1 text-xs text-slate-600 shadow-sm transition-colors",
                          "hover:border-indigo-300 hover:bg-indigo-50/50 hover:text-indigo-800",
                        )}
                      >
                        {fill}
                      </button>
                    ))}
                  </div>
                </form>
              )}

              {justSent && (
                <p role="status" className="ml-10 text-[13px] font-medium text-emerald-700">
                  Answer recorded — the graph re-enters contract. Watch the timeline below.
                </p>
              )}
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
