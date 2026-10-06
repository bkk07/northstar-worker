import { motion, useReducedMotion } from "framer-motion";
import { Bot, Send, UserRound } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ErrorState } from "@/shared/ui/feedback";
import { getErrorMessage } from "@/shared/lib/errors";
import { Card, CardBody, CardHeader } from "@/shared/ui/card";
import { PageHeader } from "@/shared/ui/page-header";
import { eventsToMessages, type ChatMessage } from "../chat/components/TaskChat";
import { useAssistant, type AssistantMessage } from "../assistant/useAssistant";
import { useTaskTimeline, useWorkerTask } from "../hooks/useWorker";

const SUGGESTIONS = ["Show open tickets", "What can you do?", "Status of my last task"] as const;

const TERMINAL = new Set(["succeeded", "failed", "cancelled"]);

/**
 * ChatGPT-style operator bot: one thread, suggestion chips, a typing
 * indicator, and a live run panel narrating the bound task's journal.
 * Decisions still happen on the task page via buttons — never typed text.
 */
export default function WorkerAssistantPage() {
  const { messages, send, busy, error, retry, activeTaskId } = useAssistant();
  const timeline = useTaskTimeline(activeTaskId ?? undefined);
  const taskQuery = useWorkerTask(activeTaskId ?? undefined);
  const task = taskQuery.data;
  const taskStatus = task?.status;

  // Task rows change outside the event stream (leases, parks); poll the
  // status pill until the run reaches a terminal state.
  useEffect(() => {
    if (!activeTaskId || !taskStatus || TERMINAL.has(taskStatus)) return;
    const timer = setInterval(() => taskQuery.refetch(), 3000);
    return () => clearInterval(timer);
  }, [activeTaskId, taskStatus, taskQuery]);

  const loadError = timeline.error ?? taskQuery.error;
  const narration = eventsToMessages(timeline.data ?? []);
  return (
    <div className="ns-page">
      <PageHeader
        title="Assistant"
        desc="Chat with the support bot — say “solve ticket TCK-…” and it runs the job."
      />
      {loadError ? (
        <ErrorState
          message={getErrorMessage(loadError)}
          onRetry={() => {
            timeline.refetch();
            taskQuery.refetch();
          }}
        />
      ) : (
        <AssistantView
          messages={messages}
          narration={narration}
          taskStatus={taskStatus}
          activeTaskId={activeTaskId}
          busy={busy || timeline.isPending}
          error={error}
          onRetry={retry}
          onSend={send}
        />
      )}
    </div>
  );
}

export function AssistantView({
  messages,
  narration,
  taskStatus,
  activeTaskId,
  busy,
  error,
  onRetry,
  onSend,
}: {
  messages: AssistantMessage[];
  narration: ChatMessage[];
  taskStatus?: string;
  activeTaskId: string | null;
  busy: boolean;
  error: string | null;
  onRetry: () => void;
  onSend: (text: string) => void;
}) {
  const [draft, setDraft] = useState("");
  const reduce = useReducedMotion();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = bottomRef.current;
    if (el && typeof el.scrollIntoView === "function") {
      el.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "end" });
    }
  }, [messages.length, narration.length, busy, reduce]);

  function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!draft.trim()) return;
    onSend(draft);
    setDraft("");
  }

  const statusLabel = taskStatus?.split("_").join(" ");
  const needsDecision =
    taskStatus === "waiting_for_approval" || taskStatus === "waiting_for_clarification";

  return (
    <Card lift={false}>
      <CardHeader
        title="Support bot"
        desc="You chat — it does the work and reports back."
        actions={
          <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700">
            <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            Online
            {statusLabel ? ` · ${statusLabel}` : ""}
          </span>
        }
      />
      <CardBody>
        <div aria-label="Assistant conversation" role="log" className="flex flex-col gap-3">
          {messages.map((message) =>
            message.from === "you" ? (
              <div key={message.id} className="flex items-start justify-end gap-2.5">
                <div className="max-w-[85%] rounded-2xl rounded-tr-md bg-slate-900 px-3.5 py-2.5 text-white">
                  <p className="whitespace-pre-wrap text-sm leading-6">{message.text}</p>
                  <p className="mt-1 text-[11px] text-slate-400">
                    You · {new Date(message.ts).toLocaleTimeString()}
                  </p>
                </div>
                <span
                  aria-hidden
                  className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-900 text-white"
                >
                  <UserRound className="h-4 w-4" />
                </span>
              </div>
            ) : (
              <motion.div
                key={message.id}
                initial={reduce ? false : { opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2 }}
                className="flex items-start gap-2.5"
              >
                <span
                  aria-hidden
                  className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-white"
                >
                  <Bot className="h-4 w-4" />
                </span>
                <div className="max-w-[85%] rounded-2xl rounded-tl-md border border-slate-200 bg-white px-3.5 py-2.5 shadow-sm">
                  <p className="whitespace-pre-wrap text-sm leading-6 text-slate-900">
                    {message.text}
                  </p>
                  <p className="mt-1 text-[11px] text-slate-400">
                    {new Date(message.ts).toLocaleTimeString()}
                  </p>
                  {(message.actions ?? []).length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-2">
                      {message.actions!.map((action) => (
                        <Link
                          key={`${action.kind}-${action.label}`}
                          to={action.href ?? "/worker"}
                          className="ns-btn ns-btn-secondary ns-btn-sm"
                        >
                          {action.label}
                        </Link>
                      ))}
                    </div>
                  )}
                </div>
              </motion.div>
            ),
          )}

          {/* Live run panel: the bound task's journal, narrated as it lands */}
          {activeTaskId && (
            <div
              aria-label="Run narration"
              role="log"
              className="ml-10 rounded-2xl border border-indigo-100 bg-indigo-50/60 p-3.5"
            >
              <p className="flex flex-wrap items-center gap-2 text-sm font-semibold text-slate-900">
                Working on task {activeTaskId.slice(0, 8)}
                {statusLabel && (
                  <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-700">
                    {statusLabel}
                  </span>
                )}
              </p>
              <div className="mt-2 flex flex-col gap-1.5">
                {narration.length === 0 && (
                  <p className="text-[13px] text-slate-500">Starting the run…</p>
                )}
                {narration.map((line) => (
                  <p key={line.key} className="text-[13px] leading-5 text-slate-700">
                    {line.text}
                  </p>
                ))}
              </div>
              {needsDecision && (
                <p className="mt-2 text-[13px] font-medium text-amber-700">
                  It needs your decision —{" "}
                  <Link
                    to={`/worker/tasks/${activeTaskId}`}
                    className="font-semibold underline"
                  >
                    open the task to decide
                  </Link>
                  .
                </p>
              )}
              {taskStatus && TERMINAL.has(taskStatus) && (
                <p className="mt-2 text-[13px]">
                  <Link
                    to={`/worker/tasks/${activeTaskId}`}
                    className="font-medium text-indigo-700 hover:underline"
                  >
                    See the full result
                  </Link>
                  .
                </p>
              )}
            </div>
          )}

          {busy && (
            <div aria-label="Bot is typing" className="flex items-start gap-2.5">
              <span
                aria-hidden
                className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-white"
              >
                <Bot className="h-4 w-4" />
              </span>
              <div className="flex items-center gap-1 rounded-2xl rounded-tl-md border border-slate-200 bg-white px-4 py-3 shadow-sm">
                {[0, 1, 2].map((dot) => (
                  <span
                    key={dot}
                    aria-hidden
                    className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400"
                    style={{ animationDelay: `${dot * 150}ms` }}
                  />
                ))}
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {messages.length <= 1 && (
          <div className="mt-3 flex flex-wrap gap-2" aria-label="Suggestions">
            {SUGGESTIONS.map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                onClick={() => onSend(suggestion)}
                className="ns-btn ns-btn-secondary ns-btn-sm"
              >
                {suggestion}
              </button>
            ))}
          </div>
        )}

        {error && (
          <p role="alert" className="mt-2 text-sm text-red-700">
            {error}{" "}
            <button type="button" onClick={onRetry} className="font-medium underline">
              Dismiss
            </button>
          </p>
        )}

        <form
          aria-label="Chat with the bot"
          onSubmit={submit}
          className="mt-3 flex gap-2 border-t border-slate-100 pt-3"
        >
          <label htmlFor="assistant-composer" className="sr-only">
            Message the bot
          </label>
          <input
            id="assistant-composer"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Say “solve ticket TCK-…”…"
            autoComplete="off"
            className="ns-input flex-1"
          />
          <button
            type="submit"
            disabled={!draft.trim() || busy}
            aria-label="Send message"
            className="ns-btn ns-btn-primary ns-btn-sm shrink-0"
          >
            <Send aria-hidden className="h-4 w-4" />
            Send
          </button>
        </form>
      </CardBody>
    </Card>
  );
}
