import { motion, useReducedMotion } from "framer-motion";
import { Bot, Check, UserRound, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ErrorState } from "@/shared/ui/feedback";
import { getErrorMessage } from "@/shared/lib/errors";
import { Badge } from "@/shared/ui/badge";
import { Card, CardBody, CardHeader } from "@/shared/ui/card";
import { ClarificationChat } from "../../clarifications/components/ClarificationChat";
import {
  useAnswerClarification,
  useApprovals,
  useClarifications,
  useCreateTask,
  useDecideApproval,
  useTaskTimeline,
} from "../../hooks/useWorker";
import type {
  ApprovalRead,
  AuditEventRead,
  ClarificationRead,
  TaskRead,
} from "../../types";

export type ChatMessage = {
  key: string;
  from: "worker" | "system";
  text: string;
  ts: string;
};

function str(value: unknown): string | null {
  return typeof value === "string" && value.length > 0 ? value : null;
}

function count(value: unknown): number | null {
  return typeof value === "number" ? value : null;
}

// Nodes worth narrating; the rest (decide/validate/observe/…) is noise the
// timeline already shows in full.
const NODE_LINES: Record<string, string> = {
  understand: "Reading the request…",
  plan: "Plan ready.",
  probe_reconcile: "Probing committed state before retrying.",
  verify: "Verifying against database state…",
};

/**
 * Journal → dialogue. Pure and unit-tested; every line is built from audit
 * facts (kinds/payloads in agent/runtime + agent/nodes), never model text.
 */
export function eventsToMessages(events: AuditEventRead[]): ChatMessage[] {
  const out: ChatMessage[] = [];
  for (const event of events) {
    const payload = event.payload ?? {};
    const say = (text: string) =>
      out.push({ key: `e${event.seq}`, from: "worker", text, ts: event.ts });
    switch (event.kind) {
      case "run.start": {
        const attempt = count(payload.attempt) ?? 1;
        say(`Run started — attempt ${attempt}.`);
        break;
      }
      case "node.transition": {
        const line = event.node ? NODE_LINES[event.node] : undefined;
        if (line) say(line);
        break;
      }
      case "contract.compiled": {
        const effects = count(payload.effects) ?? 0;
        const ambiguity = Array.isArray(payload.ambiguity)
          ? payload.ambiguity.map(String).join("; ")
          : null;
        say(
          `Contract compiled — ${effects} effect${effects === 1 ? "" : "s"} locked.` +
            (ambiguity ? ` Still needs: ${ambiguity}` : ""),
        );
        break;
      }
      case "policy.decision": {
        const rule = str(payload.rule_id) ?? "policy";
        const reason = str(payload.reason);
        const outcome = event.policy_result ?? "decided";
        say(`Policy ${outcome} — ${rule}${reason ? `: ${reason}` : ""}`);
        break;
      }
      case "tool.call": {
        say(
          event.tool === "browser_submit"
            ? "Committing via the Ops UI…"
            : `Calling ${event.tool ?? "a tool"}…`,
        );
        break;
      }
      case "failure.classified": {
        say(`Something failed (${event.error_type ?? "unknown"}). Working out recovery…`);
        break;
      }
      case "recovery.decided": {
        say(`Recovery plan: ${event.status ?? "retry"} — after ${event.error_type ?? "failure"}.`);
        break;
      }
      case "approval.park": {
        say("This step needs a human decision — the run is parked. Decide below.");
        break;
      }
      case "approval.resume": {
        say("Approved — resuming.");
        break;
      }
      case "approval.rejected": {
        say("Rejected — stopping safely with no mutation.");
        break;
      }
      case "approval.expired": {
        say("The approval request expired.");
        break;
      }
      case "clarification.park": {
        say("I need input before I can continue — answer below.");
        break;
      }
      case "clarification.answered": {
        say("Answer received — resuming.");
        break;
      }
      case "clarification.expired": {
        say("The question expired unanswered.");
        break;
      }
      case "verification.result": {
        say(`Verifier says: ${event.verification_result ?? "no verdict"}.`);
        break;
      }
      case "run.end": {
        const status = str(payload.status) ?? "ended";
        say(status === "succeeded" ? "Done — verified effects committed." : `Run ended: ${status}.`);
        break;
      }
      case "run.error": {
        say(`Run error: ${str(payload.error) ?? "see timeline"}.`);
        break;
      }
      default:
        break;
    }
  }
  return out;
}

/**
 * Per-task chat: the opening instruction, the journal narrated as worker
 * messages, approval cards with real decision buttons, the clarification
 * thread, and one input routed by state — answers an open question, or
 * starts a follow-up task. Decisions are always explicit buttons, never
 * parsed chat text.
 */
export function TaskChat({ task }: { task: TaskRead }) {
  const timeline = useTaskTimeline(task.id);
  const approvals = useApprovals();
  const clarifications = useClarifications();
  if (timeline.isPending || approvals.isPending || clarifications.isPending) return null;
  const error = timeline.error ?? approvals.error ?? clarifications.error;
  if (error)
    return (
      <ErrorState
        message={getErrorMessage(error)}
        onRetry={() => {
          timeline.refetch();
          approvals.refetch();
          clarifications.refetch();
        }}
      />
    );
  return (
    <TaskChatView
      task={task}
      events={timeline.data ?? []}
      approvals={(approvals.data ?? []).filter(
        (item) => item.task_id === task.id && item.status === "pending",
      )}
      clarifications={(clarifications.data ?? []).filter((item) => item.task_id === task.id)}
    />
  );
}

// Split for testability: pure view over a task's journal + open requests.
export function TaskChatView({
  task,
  events,
  approvals,
  clarifications,
}: {
  task: TaskRead;
  events: AuditEventRead[];
  approvals: ApprovalRead[];
  clarifications: ClarificationRead[];
}) {
  const decide = useDecideApproval();
  const answer = useAnswerClarification();
  const followup = useCreateTask();
  const [draft, setDraft] = useState("");
  const [followupId, setFollowupId] = useState<string | null>(null);
  const [approver] = useState("duty-ops");
  const reduce = useReducedMotion();
  const bottomRef = useRef<HTMLDivElement>(null);

  const messages = eventsToMessages(events);
  const openClarifications = clarifications.filter((item) => item.answer == null);
  const firstOpen = openClarifications[0];

  useEffect(() => {
    const el = bottomRef.current;
    // jsdom and very old browsers lack scrollIntoView; the thread is
    // fully readable without the auto-scroll.
    if (el && typeof el.scrollIntoView === "function") {
      el.scrollIntoView({
        behavior: reduce ? "auto" : "smooth",
        block: "end",
      });
    }
  }, [messages.length, approvals.length, clarifications.length, reduce]);

  function submit(event: React.FormEvent) {
    event.preventDefault();
    const text = draft.trim();
    if (!text) return;
    if (firstOpen && !answer.isPending) {
      answer.mutate(
        { clarificationId: firstOpen.id, answer: text, answeredBy: "duty-ops" },
        { onSuccess: () => setDraft("") },
      );
    } else if (!firstOpen && !followup.isPending) {
      followup.mutate(text, {
        onSuccess: (created) => {
          setFollowupId(created.id);
          setDraft("");
        },
      });
    }
  }

  return (
    <Card lift={false}>
      <CardHeader
        title="Chat"
        desc="Talk to the run: answer its questions here, decide approvals below. Approvals need the buttons — typed 'yes' never counts."
        actions={
          <span className="inline-flex items-center rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-medium text-indigo-700">
            {task.status.split("_").join(" ")}
          </span>
        }
      />
      <CardBody>
        <div aria-label="Task conversation" role="log" className="flex flex-col gap-3">
          {/* Opening instruction */}
          <div className="flex items-start justify-end gap-2.5">
            <div className="max-w-[85%] rounded-2xl rounded-tr-md bg-slate-900 px-3.5 py-2.5 text-white">
              <p className="text-sm leading-6">{task.text}</p>
              <p className="mt-1 text-[11px] text-slate-400">
                You · {new Date(task.created_at).toLocaleString()}
              </p>
            </div>
            <span
              aria-hidden
              className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-900 text-white"
            >
              <UserRound className="h-4 w-4" />
            </span>
          </div>

          {/* Narrated journal */}
          {messages.map((message) => (
            <motion.div
              key={message.key}
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
                <p className="text-sm leading-6 text-slate-900">{message.text}</p>
                <p className="mt-1 text-[11px] text-slate-400">
                  {new Date(message.ts).toLocaleTimeString()}
                </p>
              </div>
            </motion.div>
          ))}

          {/* Embedded approval decisions */}
          {approvals.map((approval) => (
            <motion.div
              key={approval.id}
              initial={reduce ? false : { opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2 }}
              aria-label={`Approval ${approval.id}`}
              className="ml-10 rounded-2xl border border-amber-200 bg-amber-50/60 p-3.5"
            >
              <p className="flex flex-wrap items-center gap-2 text-sm font-semibold text-slate-900">
                {approval.requested_action}
                <Badge tone="human_approval">{approval.policy_rule_id}</Badge>
              </p>
              <p className="mt-1 text-[13px] leading-5 text-slate-600">{approval.reason}</p>
              <div className="mt-2.5 flex gap-2">
                <button
                  type="button"
                  disabled={decide.isPending}
                  onClick={() =>
                    decide.mutate({ approvalId: approval.id, decision: "approve", approver })
                  }
                  className="ns-btn ns-btn-success ns-btn-sm"
                >
                  <Check aria-hidden className="h-3.5 w-3.5" />
                  Approve
                </button>
                <button
                  type="button"
                  disabled={decide.isPending}
                  onClick={() =>
                    decide.mutate({ approvalId: approval.id, decision: "reject", approver })
                  }
                  className="ns-btn ns-btn-danger ns-btn-sm"
                >
                  <X aria-hidden className="h-3.5 w-3.5" />
                  Reject
                </button>
              </div>
            </motion.div>
          ))}
          {decide.isSuccess && (
            <p role="status" className="ml-10 text-[13px] font-medium text-emerald-700">
              Decision recorded as {approver}; the task requeued.
            </p>
          )}

          {/* Clarification thread lives inside the conversation */}
          <ClarificationChat taskId={task.id} taskStatus={task.status} bare />

          {followupId && (
            <p role="status" className="text-[13px] text-slate-600">
              Follow-up started as a new task —{" "}
              <Link to={`/worker/tasks/${followupId}`} className="font-medium text-indigo-700 hover:underline">
                open it here
              </Link>
              .
            </p>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Routed input: answers an open question, else starts a follow-up */}
        <form
          aria-label="Chat reply"
          onSubmit={submit}
          className="mt-3 flex gap-2 border-t border-slate-100 pt-3"
        >
          <label htmlFor="task-chat-reply" className="sr-only">
            Reply
          </label>
          <input
            id="task-chat-reply"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder={
              firstOpen
                ? "Answer the worker's question…"
                : "Ask a follow-up — starts a new task…"
            }
            autoComplete="off"
            className="ns-input flex-1"
          />
          <button
            type="submit"
            disabled={!draft.trim() || answer.isPending || followup.isPending}
            className="ns-btn ns-btn-primary ns-btn-sm shrink-0"
          >
            Send
          </button>
        </form>
        {(decide.isError || answer.isError || followup.isError) && (
          <p role="alert" className="mt-2 text-sm text-red-700">
            {getErrorMessage(decide.error ?? answer.error ?? followup.error)}
          </p>
        )}
      </CardBody>
    </Card>
  );
}
