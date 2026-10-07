import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Bot, Check, Circle, Loader2, MessageSquarePlus, Plus, Send, Trash2, UserRound } from "lucide-react";
import { Badge, Button, Card } from "@/components/ui";
import { staffApiErrorMessage } from "@/lib/api-client";
import { useStaffAuth } from "@/stores/auth-store";
import { useSupportChat } from "@/hooks/useSupportChat";
import {
  answerClarification,
  decideWorkerApproval,
  fetchPendingClarifications,
  fetchTaskEvents,
  fetchTaskEvidence,
  fetchWorkerTask,
  type ChatAction,
  type PendingClarification,
  type WorkerTaskStatus,
} from "@/services/chat-api";
import {
  decideApproval as decideTicketApproval,
  fetchTrace,
} from "@/services/support-api";

const SUGGESTIONS = [
  "Show open tickets",
  "Anything waiting for approval?",
  "What's the refund policy?",
  "Status of my last task",
] as const;

const TERMINAL_TASK = new Set(["succeeded", "failed", "blocked", "inconclusive", "cancelled"]);

function extractTicketCode(action: ChatAction): string | null {
  const hay = `${action.label} ${action.href ?? ""}`;
  const m = hay.match(/\b(?:TCK|TKT)-[A-Z0-9]{3,}\b/i);
  return m ? m[0].toUpperCase() : null;
}

function extractOrderCode(action: ChatAction): string | null {
  const hay = `${action.label} ${action.href ?? ""}`;
  const m = hay.match(/\bORD-[A-Z0-9]{3,}\b/i);
  return m ? m[0].toUpperCase() : null;
}

function approvalGroups(actions: ChatAction[]): ChatAction[][] {
  const byId = new Map<string, ChatAction[]>();
  for (const a of actions) {
    if (a.kind !== "approval" || !a.approval_id) continue;
    const g = byId.get(a.approval_id) ?? [];
    g.push(a);
    byId.set(a.approval_id, g);
  }
  return [...byId.values()];
}

function ActionRow({
  actions,
  onSend,
  onDecide,
  deciding,
  decidedIds,
}: {
  actions: ChatAction[];
  onSend: (text: string) => void;
  onDecide: (approvalId: string, decision: "approve" | "reject") => void;
  deciding: string | null;
  decidedIds: string[];
}) {
  const approvals = approvalGroups(actions);
  const others = actions.filter((a) => a.kind !== "approval");

  return (
    <div className="mt-2 flex flex-col gap-2">
      {approvals.map(
        (group) =>
          !decidedIds.includes(group[0].approval_id!) && (
            <div
              key={group[0].approval_id}
              className="flex flex-wrap gap-2 rounded-xl bg-amber-50 p-2"
            >
              {group.map((a) => (
                <button
                  key={`${a.approval_id}-${a.decision}`}
                  type="button"
                  disabled={deciding === a.approval_id}
                  onClick={() =>
                    onDecide(a.approval_id!, a.decision === "reject" ? "reject" : "approve")
                  }
                  className={`sp-btn ${a.decision === "reject" ? "sp-btn-secondary" : "sp-btn-primary"}`}
                  style={{ padding: "0.375rem 0.75rem", fontSize: 13 }}
                >
                  {deciding === a.approval_id ? "Working…" : a.label}
                </button>
              ))}
            </div>
          ),
      )}
      {others.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {others.map((a, i) => {
            const ticketCode = extractTicketCode(a);
            const orderCode = extractOrderCode(a);
            // Ticket open -> deep-link into the queue search (support-web uses id routes).
            if (a.kind === "ticket" && ticketCode) {
              return (
                <span key={`${a.label}-${i}`} className="flex flex-wrap gap-2">
                  <Link
                    to={`/tickets?q=${encodeURIComponent(ticketCode)}`}
                    className="sp-btn sp-btn-secondary"
                    style={{ padding: "0.375rem 0.75rem", fontSize: 13 }}
                  >
                    Open {ticketCode}
                  </Link>
                  <button
                    type="button"
                    className="sp-btn sp-btn-secondary"
                    style={{ padding: "0.375rem 0.75rem", fontSize: 13 }}
                    onClick={() => onSend(`Tell me about ${ticketCode}`)}
                  >
                    Ask about {ticketCode}
                  </button>
                </span>
              );
            }
            if (a.kind === "tickets") {
              return (
                <Link
                  key={`${a.label}-${i}`}
                  to="/tickets"
                  className="sp-btn sp-btn-secondary"
                  style={{ padding: "0.375rem 0.75rem", fontSize: 13 }}
                >
                  {a.label}
                </Link>
              );
            }
            if (a.kind === "solve" && ticketCode) {
              return (
                <button
                  key={`${a.label}-${i}`}
                  type="button"
                  className="sp-btn sp-btn-secondary"
                  style={{ padding: "0.375rem 0.75rem", fontSize: 13 }}
                  onClick={() => onSend(`Solve ticket ${ticketCode}`)}
                >
                  {a.label}
                </button>
              );
            }
            if (a.kind === "order" && orderCode) {
              return (
                <button
                  key={`${a.label}-${i}`}
                  type="button"
                  className="sp-btn sp-btn-secondary"
                  style={{ padding: "0.375rem 0.75rem", fontSize: 13 }}
                  onClick={() => onSend(`Show order ${orderCode}`)}
                >
                  {a.label}
                </button>
              );
            }
            if (a.kind === "task" && a.task_id) {
              const short = String(a.task_id).slice(0, 8);
              return (
                <button
                  key={`${a.label}-${i}`}
                  type="button"
                  className="sp-btn sp-btn-secondary"
                  style={{ padding: "0.375rem 0.75rem", fontSize: 13 }}
                  onClick={() => onSend(`Status of task ${short}`)}
                >
                  {a.label}
                </button>
              );
            }
            // Internal support-web links pass through; worker/ops/shop
            // hrefs become chat follow-ups so nothing 404s.
            if (a.href && ["/tickets", "/dashboard", "/chat"].some((p) => a.href!.startsWith(p))) {
              return (
                <Link
                  key={`${a.label}-${i}`}
                  to={a.href}
                  className="sp-btn sp-btn-secondary"
                  style={{ padding: "0.375rem 0.75rem", fontSize: 13 }}
                >
                  {a.label}
                </Link>
              );
            }
            return (
              <button
                key={`${a.label}-${i}`}
                type="button"
                className="sp-btn sp-btn-secondary"
                style={{ padding: "0.375rem 0.75rem", fontSize: 13 }}
                onClick={() => {
                  if (ticketCode) onSend(`Tell me about ${ticketCode}`);
                  else if (orderCode) onSend(`Show order ${orderCode}`);
                  else onSend(a.label);
                }}
              >
                {a.label}
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}

export function ChatPage() {
  const [params, setParams] = useSearchParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const staffEmail = useStaffAuth((s) => s.user?.email) ?? "staff";
  const sid = params.get("sid");

  const {
    messages,
    send,
    appendBot,
    newChat,
    switchSession,
    removeSession,
    sessions,
    activeSessionId,
    busy,
    error,
    retry,
    activeTaskId,
    activeTicketId,
  } = useSupportChat(sid);

  const [draft, setDraft] = useState("");
  const [solveCode, setSolveCode] = useState<string | null>(null);
  const [deciding, setDeciding] = useState<string | null>(null);
  const [decidedIds, setDecidedIds] = useState<string[]>([]);
  const handledDeepLink = useRef(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Deep links: /chat?new=1&solve=TCK-… (from a ticket) opens a fresh
  // thread with an editable draft so staff can add context before Send.
  // ?ticket=TCK-… prefills "Tell me about …", ?draft=… prefills raw text.
  useEffect(() => {
    if (handledDeepLink.current) return;
    handledDeepLink.current = true;
    const wantNew = params.get("new") === "1";
    const solve = (params.get("solve") ?? "").toUpperCase().trim();
    const ticket = (params.get("ticket") ?? "").toUpperCase().trim();
    const rawDraft = params.get("draft") ?? "";

    if (solve || ticket || wantNew || rawDraft) {
      if (solve || wantNew) newChat();
      if (solve) {
        setSolveCode(solve);
        setDraft(`Solve ticket ${solve} — `);
      } else if (ticket) {
        setSolveCode(ticket);
        setDraft(`Tell me about ${ticket} — `);
      } else if (rawDraft) {
        setDraft(rawDraft);
      }
      const next = new URLSearchParams(params);
      next.delete("new");
      next.delete("solve");
      next.delete("ticket");
      next.delete("draft");
      if (activeSessionId) next.set("sid", activeSessionId);
      setParams(next, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ?sid= switches swap the thread without remounting.
  useEffect(() => {
    if (sid && sid !== activeSessionId) switchSession(sid);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sid]);

  // Keep ?sid= in the URL so refresh / back keeps the thread.
  useEffect(() => {
    if (activeSessionId && params.get("sid") !== activeSessionId) {
      const next = new URLSearchParams(params);
      next.set("sid", activeSessionId);
      setParams(next, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeSessionId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, busy]);

  const taskQuery = useQuery({
    queryKey: ["support-chat-task", activeTaskId],
    queryFn: () => fetchWorkerTask(activeTaskId!),
    enabled: !!activeTaskId,
    refetchInterval: (query) => {
      const d = query.state.data as WorkerTaskStatus | undefined;
      return d && !TERMINAL_TASK.has(d.status) ? 3000 : false;
    },
  });
  const taskStatus = taskQuery.data?.status;
  const statusLabel = useMemo(() => taskStatus?.split("_").join(" "), [taskStatus]);

  // Live progress: poll the run's audit trail while active and narrate the
  // latest step in plain words instead of a bare "Working on task …".
  const eventsQuery = useQuery({
    queryKey: ["support-chat-task-events", activeTaskId],
    queryFn: () => fetchTaskEvents(activeTaskId!),
    enabled: !!activeTaskId && !!taskStatus && !TERMINAL_TASK.has(taskStatus),
    refetchInterval: 3000,
  });
  const progressLine = useMemo(() => {
    const events = eventsQuery.data ?? [];
    if (events.length === 0) return null;
    const last = events[events.length - 1];
    const step = last.tool ?? last.node;
    if (!step) return null;
    const friendly: Record<string, string> = {
      understand: "Reading your ticket",
      contract: "Locking in the plan",
      plan: "Planning the fix",
      decide: "Choosing the next step",
      validate: "Double-checking the details",
      policy_check: "Checking the policy",
      human_approval: "Waiting on a decision",
      execute: "Doing the work",
      observe: "Reading the result",
      verify: "Verifying it stuck",
      finalize: "Wrapping up",
    };
    const label = friendly[step] ?? step.split("_").join(" ");
    if (last.tool) return `${label} — ${last.tool}`;
    return label;
  }, [eventsQuery.data]);

  // Narrate terminal failure once: a task that ends failed/blocked/
  // inconclusive/cancelled must say why instead of just showing a pill.
  const narratedTasks = useRef<Set<string>>(new Set());
  useEffect(() => {
    if (!activeTaskId || !taskStatus) return;
    const short = activeTaskId.slice(0, 8);
    if (
      messages.some((m) => m.from === "bot" && m.text.startsWith(`Task ${short} ${taskStatus}`))
    ) {
      narratedTasks.current.add(activeTaskId);
      return;
    }
    if (!TERMINAL_TASK.has(taskStatus) || taskStatus === "succeeded") return;
    if (narratedTasks.current.has(activeTaskId)) return;
    narratedTasks.current.add(activeTaskId);
    fetchTaskEvidence(activeTaskId).then((ev) => {
      if (ev?.summary) {
        appendBot(`Task ${short} ${taskStatus}: ${ev.summary}`);
      } else {
        appendBot(
          `Task ${short} ended as ${taskStatus} without reporting back. ` +
            `Open the task for details, or retry it from the ticket.`,
        );
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTaskId, taskStatus, messages]);

  // Clarifications: when the run parks with a question, surface it in chat
  // with an answer box instead of a silent "waiting" pill.
  const clarQuery = useQuery({
    queryKey: ["support-chat-clarifications", activeTaskId],
    queryFn: fetchPendingClarifications,
    enabled: !!activeTaskId && taskStatus === "waiting_for_clarification",
    refetchInterval: 4000,
  });
  const myClars: PendingClarification[] = (clarQuery.data ?? []).filter(
    (c) => !activeTaskId || c.task_id === activeTaskId,
  );
  const askedClars = useRef<Set<string>>(new Set());
  const [clarAnswer, setClarAnswer] = useState("");
  const [clarSending, setClarSending] = useState(false);
  useEffect(() => {
    for (const c of myClars) {
      if (askedClars.current.has(c.id)) continue;
      askedClars.current.add(c.id);
      appendBot(`I need your help before I can continue: ${c.question}`);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [myClars]);

  async function sendClarAnswer(id: string) {
    if (!clarAnswer.trim() || clarSending) return;
    setClarSending(true);
    try {
      await answerClarification(id, clarAnswer.trim(), staffEmail);
      appendBot("Got it — the run resumes on its own.");
      setClarAnswer("");
      void qc.invalidateQueries({ queryKey: ["support-chat-task"] });
      void clarQuery.refetch();
    } catch (e) {
      appendBot(`That answer didn't land: ${staffApiErrorMessage(e, "Answer failed.")}`);
    } finally {
      setClarSending(false);
    }
  }

  async function onDecide(approvalId: string, decision: "approve" | "reject") {
    setDeciding(approvalId);
    try {
      await decideWorkerApproval(approvalId, decision, staffEmail);
      setDecidedIds((p) => [...p, approvalId]);
      appendBot(
        `${decision === "approve" ? "Approved" : "Rejected"} — the run resumes on its own.`,
      );
      void qc.invalidateQueries({ queryKey: ["support-chat-task"] });
    } catch (e) {
      appendBot(`That decision didn't land: ${staffApiErrorMessage(e, "Decision failed.")}`);
    } finally {
      setDeciding(null);
    }
  }

  // Ticket-grounded thread: live trace, approvals, and customer-waits for
  // the bound ticket run (the same run the ticket page drives).
  const TERMINAL_TICKET_RUN = ["COMPLETED", "CANCELLED", "FAILED"];
  const ticketTrace = useQuery({
    queryKey: ["support-chat-ticket-trace", activeTicketId],
    queryFn: () => fetchTrace(activeTicketId!),
    enabled: !!activeTicketId,
    retry: 1,
    refetchInterval: (query) => {
      const d = query.state.data as { run?: { status: string } | null } | undefined;
      return d?.run && !TERMINAL_TICKET_RUN.includes(d.run.status) ? 2500 : false;
    },
  });
  const ticketRun = ticketTrace.data?.run ?? null;
  const ticketStatus = ticketTrace.data?.ticket_status ?? null;
  const ticketApprovals = (ticketTrace.data?.approvals ?? []).filter(
    (a) => a.status === "PENDING",
  );
  const narratedTicketRuns = useRef<Set<string>>(new Set());
  useEffect(() => {
    if (!activeTicketId || !ticketRun) return;
    if (TERMINAL_TICKET_RUN.includes(ticketRun.status)) return;
    if (narratedTicketRuns.current.has(ticketRun.id)) return;
    if (ticketStatus === "WAITING_FOR_HUMAN" && ticketApprovals.length > 0) {
      narratedTicketRuns.current.add(ticketRun.id);
      appendBot(
        `Ticket run needs your approval: ${ticketApprovals[0].action_type} — ` +
          `use Approve / Reject below and it resumes on its own.`,
      );
    } else if (ticketStatus === "WAITING_FOR_CUSTOMER") {
      narratedTicketRuns.current.add(ticketRun.id);
      appendBot(
        "Ticket run is waiting on the customer — the question is in the ticket conversation.",
      );
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTicketId, ticketRun?.id, ticketStatus, ticketApprovals.length]);

  async function onDecideTicket(approvalId: string, approved: boolean) {
    setDeciding(approvalId);
    try {
      await decideTicketApproval(approvalId, approved);
      setDecidedIds((p) => [...p, approvalId]);
      appendBot(
        `${approved ? "Approved" : "Rejected"} — the ticket run resumes on its own.`,
      );
      void qc.invalidateQueries({ queryKey: ["support-chat-ticket-trace"] });
    } catch (e) {
      appendBot(`That decision didn't land: ${staffApiErrorMessage(e, "Decision failed.")}`);
    } finally {
      setDeciding(null);
    }
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!draft.trim() || busy) return;
    setSolveCode(null);
    send(draft);
    setDraft("");
  }

  function startNew() {
    newChat();
    setDraft("");
    setSolveCode(null);
    setParams({}, { replace: true });
  }

  function openSession(id: string) {
    switchSession(id);
    setDraft("");
    setSolveCode(null);
    setParams({ sid: id }, { replace: true });
  }

  return (
    <div className="grid items-start gap-4 xl:grid-cols-[240px_minmax(0,1fr)]">
      <Card className="!p-3">
        <Button className="w-full" onClick={startNew}>
          <Plus size={15} aria-hidden /> New chat
        </Button>
        <p className="sp-muted mb-2 mt-3 px-1 text-xs font-semibold uppercase tracking-wider">
          History
        </p>
        {sessions.length === 0 ? (
          <p className="sp-muted px-1 text-[13px]">No conversations yet.</p>
        ) : (
          <ul className="flex max-h-[60vh] flex-col gap-1 overflow-y-auto">
            {sessions.map((s) => (
              <li key={s.id} className="group flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => openSession(s.id)}
                  className={`min-w-0 flex-1 truncate rounded-md px-2 py-1.5 text-left text-[13px] ${
                    s.id === activeSessionId
                      ? "bg-indigo-50 font-semibold text-indigo-800"
                      : "hover:bg-slate-50"
                  }`}
                  title={s.title}
                >
                  {s.title}
                </button>
                <button
                  type="button"
                  aria-label={`Delete ${s.title}`}
                  className="rounded-md p-1 text-slate-400 opacity-0 hover:bg-red-50 hover:text-red-600 group-hover:opacity-100"
                  onClick={() => removeSession(s.id)}
                >
                  <Trash2 size={13} aria-hidden />
                </button>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card className="flex min-h-[70vh] flex-col">
        <div className="ns-row-between">
          <h1 className="flex items-center gap-1.5 text-sm font-semibold">
            <MessageSquarePlus size={15} aria-hidden className="text-indigo-600" /> AI Chat — talk
            directly
          </h1>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700">
            <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            Online{statusLabel ? ` · ${statusLabel}` : ""}
          </span>
        </div>

        {solveCode ? (
          <div className="mt-3 rounded-xl border border-indigo-200 bg-indigo-50 px-3 py-2 text-[13px]">
            <span className="font-semibold">Ticket {solveCode} loaded.</span> Add any extra
            context in the box below, then press Send — nothing runs until you send.{" "}
            <button
              type="button"
              className="font-medium text-indigo-700 hover:underline"
              onClick={() => nav(`/tickets?q=${encodeURIComponent(solveCode)}`)}
            >
              View ticket
            </button>
          </div>
        ) : (
          <p className="sp-muted mt-2 text-[13px]">
            Say “solve ticket TCK-…” with context and the AI runs it here. Approvals use the
            buttons — typed “yes” never counts.
          </p>
        )}

        <div aria-label="Support chat conversation" role="log" className="mt-3 flex flex-1 flex-col gap-3 overflow-y-auto pr-0.5">
          {messages.map((m) =>
            m.from === "you" ? (
              <div key={m.id} className="flex items-start justify-end gap-2.5">
                <div className="max-w-[85%] rounded-2xl rounded-tr-md bg-slate-900 px-3.5 py-2.5 text-white">
                  <p className="whitespace-pre-wrap text-sm leading-6">{m.text}</p>
                  <p className="mt-1 text-[11px] text-slate-400">
                    You · {new Date(m.ts).toLocaleTimeString()}
                  </p>
                </div>
                <span
                  aria-hidden
                  className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-900 text-white"
                >
                  <UserRound size={15} />
                </span>
              </div>
            ) : (
              <div key={m.id} className="flex items-start gap-2.5">
                <span
                  aria-hidden
                  className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-white"
                >
                  <Bot size={15} />
                </span>
                <div className="max-w-[85%] rounded-2xl rounded-tl-md border border-slate-200 bg-white px-3.5 py-2.5 shadow-sm">
                  <p className="whitespace-pre-wrap text-sm leading-6 text-slate-900">{m.text}</p>
                  <p className="mt-1 text-[11px] text-slate-400">
                    {new Date(m.ts).toLocaleTimeString()}
                  </p>
                  {(m.actions ?? []).length > 0 ? (
                    <ActionRow
                      actions={m.actions!}
                      onSend={send}
                      onDecide={(id, d) => void onDecide(id, d)}
                      deciding={deciding}
                      decidedIds={decidedIds}
                    />
                  ) : null}
                </div>
              </div>
            ),
          )}

          {activeTaskId ? (
            <div className="ml-10 rounded-2xl border border-indigo-100 bg-indigo-50/60 p-3.5">
              <p className="flex flex-wrap items-center gap-2 text-sm font-semibold text-slate-900">
                Working on task {activeTaskId.slice(0, 8)}
                {statusLabel ? (
                  <Badge tone="info">{statusLabel}</Badge>
                ) : null}
              </p>
              <p className="mt-1 text-[13px] text-slate-500">
                {taskQuery.isPending
                  ? "Starting the run…"
                  : taskStatus && !TERMINAL_TASK.has(taskStatus)
                    ? (progressLine ?? "Reading your ticket…")
                    : `Status: ${taskStatus ?? "unknown"} — ask “status of my last task” anytime for an update.`}
              </p>
              {taskStatus === "waiting_for_clarification" && myClars.length > 0 ? (
                <form
                  className="mt-2 flex gap-2"
                  onSubmit={(e) => {
                    e.preventDefault();
                    void sendClarAnswer(myClars[0].id);
                  }}
                >
                  <input
                    className="sp-input flex-1"
                    placeholder={`Answer: ${myClars[0].question.slice(0, 60)}…`}
                    value={clarAnswer}
                    onChange={(e) => setClarAnswer(e.target.value)}
                    aria-label="Answer the run's question"
                  />
                  <Button type="submit" disabled={!clarAnswer.trim() || clarSending}>
                    {clarSending ? "Sending…" : "Answer"}
                  </Button>
                </form>
              ) : null}
            </div>
          ) : null}

          {activeTicketId ? (
            <div className="ml-10 rounded-2xl border border-emerald-100 bg-emerald-50/60 p-3.5">
              <p className="flex flex-wrap items-center gap-2 text-sm font-semibold text-slate-900">
                Ticket run
                {ticketRun?.intent ? (
                  <Badge tone="info">{ticketRun.intent}</Badge>
                ) : null}
                {ticketStatus ? (
                  <Badge tone="info">{ticketStatus.split("_").join(" ").toLowerCase()}</Badge>
                ) : null}
                <Link
                  to={`/tickets/${activeTicketId}`}
                  className="text-[13px] font-medium text-indigo-700 hover:underline"
                >
                  Open ticket
                </Link>
              </p>
              {ticketTrace.isPending ? (
                <p className="mt-1 text-[13px] text-slate-500">Starting the run — first step lands in a few seconds…</p>
              ) : ticketTrace.isError ? (
                <p className="mt-1 text-[13px] text-slate-500">
                  Couldn’t load the run timeline.{" "}
                  <button
                    type="button"
                    className="font-medium text-indigo-700 underline"
                    onClick={() => void ticketTrace.refetch()}
                  >
                    Retry
                  </button>{" "}
                  or follow it on the ticket page.
                </p>
              ) : ticketApprovals.length > 0 ? (
                <div className="mt-2 flex flex-col gap-2">
                  {ticketApprovals
                    .filter((a) => !decidedIds.includes(a.id))
                    .map((a) => (
                      <div key={a.id} className="rounded-xl bg-amber-50 p-2">
                        <p className="text-[13px] font-medium text-slate-800">
                          Approval: {a.action_type} — use the buttons, typed “yes” never counts.
                        </p>
                        <div className="mt-1.5 flex gap-2">
                          <Button
                            variant="secondary"
                            disabled={deciding === a.id}
                            onClick={() => void onDecideTicket(a.id, false)}
                          >
                            {deciding === a.id ? "Working…" : "Reject"}
                          </Button>
                          <Button
                            disabled={deciding === a.id}
                            onClick={() => void onDecideTicket(a.id, true)}
                          >
                            {deciding === a.id ? "Working…" : "Approve"}
                          </Button>
                        </div>
                      </div>
                    ))}
                </div>
              ) : ticketStatus === "WAITING_FOR_CUSTOMER" ? (
                <p className="mt-1 text-[13px] text-slate-500">
                  Waiting on the customer — the question is in the ticket conversation.
                </p>
              ) : (
                <ol className="mt-2 flex flex-col gap-0" aria-live="polite">
                  {(ticketTrace.data?.steps ?? []).map((s, i, arr) => (
                    <li key={s.key} className="flex gap-2.5">
                      <div className="flex flex-col items-center">
                        <span className={s.state === "done" ? "text-emerald-600" : s.state === "active" ? "text-indigo-600" : "text-slate-300"}>
                          {s.state === "done" ? (
                            <Check size={16} aria-hidden />
                          ) : s.state === "active" ? (
                            <Loader2 size={16} aria-hidden className="animate-spin" />
                          ) : (
                            <Circle size={16} aria-hidden />
                          )}
                        </span>
                        {i < arr.length - 1 ? (
                          <span className={`h-4 w-px ${s.state === "done" ? "bg-emerald-200" : "bg-slate-200"}`} aria-hidden />
                        ) : null}
                      </div>
                      <p className={`pb-2.5 text-[13px] ${s.state === "todo" ? "text-slate-400" : "font-medium text-slate-800"}`}>
                        {s.label}
                        {s.detail ? (
                          <span className="mt-0.5 block font-mono text-xs font-normal text-slate-500">
                            {s.detail}
                          </span>
                        ) : null}
                      </p>
                    </li>
                  ))}
                </ol>
              )}
            </div>
          ) : null}

          {busy ? (
            <div aria-label="Bot is typing" className="flex items-start gap-2.5">
              <span
                aria-hidden
                className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-white"
              >
                <Bot size={15} />
              </span>
              <div className="flex items-center gap-1 rounded-2xl rounded-tl-md border border-slate-200 bg-white px-4 py-3 shadow-sm">
                {[0, 1, 2].map((d) => (
                  <span
                    key={d}
                    aria-hidden
                    className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400"
                    style={{ animationDelay: `${d * 150}ms` }}
                  />
                ))}
              </div>
            </div>
          ) : null}
          <div ref={bottomRef} />
        </div>

        {messages.length <= 1 ? (
          <div className="mt-3 flex flex-wrap gap-2" aria-label="Suggestions">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => send(s)}
                className="sp-btn sp-btn-secondary"
                style={{ padding: "0.375rem 0.75rem", fontSize: 13 }}
              >
                {s}
              </button>
            ))}
          </div>
        ) : null}

        {error ? (
          <p role="alert" className="mt-2 text-sm text-red-700">
            {error}{" "}
            <button type="button" onClick={retry} className="font-medium underline">
              Dismiss
            </button>
          </p>
        ) : null}

        <form aria-label="Chat with the support AI" onSubmit={submit} className="mt-3 flex gap-2 border-t border-slate-100 pt-3">
          <label htmlFor="support-chat-composer" className="sr-only">
            Message the support AI
          </label>
          <textarea
            id="support-chat-composer"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                if (draft.trim() && !busy) {
                  setSolveCode(null);
                  send(draft);
                  setDraft("");
                }
              }
            }}
            placeholder="Say “solve ticket TCK-… ” + add context… (Enter to send, Shift+Enter for new line)"
            rows={3}
            className="sp-input flex-1 resize-y"
          />
          <Button type="submit" disabled={!draft.trim() || busy} aria-label="Send message" className="shrink-0 self-end">
            <Send size={15} aria-hidden /> Send
          </Button>
        </form>
        <p className="sp-muted mt-1.5 text-xs">
          Clear-cut: nothing runs until you press Send. Each ticket gets its own chat via “Solve
          in chat”.
        </p>
      </Card>
    </div>
  );
}
