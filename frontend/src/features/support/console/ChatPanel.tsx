import { motion, useReducedMotion } from "framer-motion";
import { Bot, Send, UserRound } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import type { AssistantMessage } from "@/features/worker/assistant/useAssistant";
import type { AssistantAction } from "@/features/worker/assistant/assistantApi";
import type { ChatMessage } from "@/features/worker/chat/components/TaskChat";
import { Card, CardBody, CardHeader } from "@/shared/ui/card";

const SUGGESTIONS = [
  "Show open tickets",
  "Anything waiting for approval?",
  "What's the refund policy?",
  "Status of my last task",
] as const;

const TERMINAL = new Set(["succeeded", "failed", "cancelled"]);

/** Group inline approval actions by their approval id. */
function approvalGroups(actions: AssistantAction[]): AssistantAction[][] {
  const byId = new Map<string, AssistantAction[]>();
  for (const action of actions) {
    if (action.kind !== "approval" || !action.approval_id) continue;
    const group = byId.get(action.approval_id) ?? [];
    group.push(action);
    byId.set(action.approval_id, group);
  }
  return [...byId.values()];
}

/**
 * Bot thread: user/bot bubbles, inline Approve/Reject buttons bound to
 * approval ids (explicit POSTs — typed text never decides), link actions,
 * and the live run narration for the bound task.
 */
export function ChatPanel({
  messages,
  narration,
  taskStatus,
  activeTaskId,
  busy,
  error,
  deciding,
  onRetry,
  onSend,
  onDecide,
}: {
  messages: AssistantMessage[];
  narration: ChatMessage[];
  taskStatus?: string;
  activeTaskId: string | null;
  busy: boolean;
  error: string | null;
  deciding: string | null;
  onRetry: () => void;
  onSend: (text: string) => void;
  onDecide: (approvalId: string, decision: "approve" | "reject") => void;
}) {
  const [draft, setDraft] = useState("");
  const [decidedIds, setDecidedIds] = useState<string[]>([]);
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

  function decide(approvalId: string, decision: "approve" | "reject") {
    setDecidedIds((previous) => [...previous, approvalId]);
    onDecide(approvalId, decision);
  }

  const statusLabel = taskStatus?.split("_").join(" ");
  const needsDecision =
    taskStatus === "waiting_for_approval" || taskStatus === "waiting_for_clarification";

  return (
    <Card lift={false} className="flex min-h-0 flex-1 flex-col">
      <CardHeader
        title="Support bot"
        desc="Ask anything — or hand me a ticket and watch it get solved."
        actions={
          <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700">
            <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            Online
            {statusLabel ? ` · ${statusLabel}` : ""}
          </span>
        }
      />
      <CardBody className="flex min-h-0 flex-1 flex-col">
        <div aria-label="Assistant conversation" role="log" className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto pr-0.5">
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
                  {(message.actions ?? []).filter((a) => a.kind !== "approval").length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-2">
                      {message.actions!
                        .filter((action) => action.kind !== "approval")
                        .map((action) => (
                          <Link
                            key={`${action.kind}-${action.label}`}
                            to={action.href ?? "/worker/assistant"}
                            className="ns-btn ns-btn-secondary ns-btn-sm"
                          >
                            {action.label}
                          </Link>
                        ))}
                    </div>
                  )}
                  {approvalGroups(message.actions ?? []).map(
                    (group) =>
                      !decidedIds.includes(group[0].approval_id!) && (
                        <div
                          key={group[0].approval_id}
                          className="mt-2 flex flex-wrap gap-2 rounded-xl bg-amber-50 p-2"
                        >
                          {group.map((action) => (
                            <button
                              key={`${action.approval_id}-${action.decision}`}
                              type="button"
                              disabled={deciding === action.approval_id}
                              onClick={() =>
                                decide(
                                  action.approval_id!,
                                  action.decision === "reject" ? "reject" : "approve",
                                )
                              }
                              className={
                                action.decision === "reject"
                                  ? "ns-btn ns-btn-secondary ns-btn-sm"
                                  : "ns-btn ns-btn-primary ns-btn-sm"
                              }
                            >
                              {deciding === action.approval_id ? "Working…" : action.label}
                            </button>
                          ))}
                        </div>
                      ),
                  )}
                </div>
              </motion.div>
            ),
          )}

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
                  It needs your decision — use the buttons above
                  {` or `}
                  <Link
                    to={`/worker/tasks/${activeTaskId}`}
                    className="font-semibold underline"
                  >
                    open the task
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
            placeholder="Ask about a ticket, order, product, or policy…"
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
