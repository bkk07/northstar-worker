import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Circle, Loader2, Sparkles } from "lucide-react";
import { Button, Card } from "@/components/ui";
import { staffApiErrorMessage } from "@/lib/api-client";
import {
  solveTicket,
  fetchTrace,
  subscribeActivity,
  takeOverTicket,
} from "@/services/support-api";
import { ApprovalCard } from "./ApprovalCard";

const TERMINAL_RUNS = ["COMPLETED", "CANCELLED", "FAILED"];

export function AICopilot({
  ticketId,
  ticketNumber,
  ticketStatus,
  onChanged,
}: {
  ticketId: string;
  ticketNumber: string;
  ticketStatus: string;
  onChanged: () => void;
}) {
  const qc = useQueryClient();
  const nav = useNavigate();
  const [solving, setSolving] = useState(false);
  const [takingOver, setTakingOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [liveFeed, setLiveFeed] = useState<string[]>([]);

  const trace = useQuery({
    queryKey: ["support-trace", ticketId],
    queryFn: () => fetchTrace(ticketId),
    refetchInterval: (query) => {
      const d = query.state.data as { run?: { status: string } | null } | undefined;
      return d?.run && !TERMINAL_RUNS.includes(d.run.status) ? 4000 : false;
    },
  });

  const runActive = !!trace.data?.run && !TERMINAL_RUNS.includes(trace.data.run.status);

  useEffect(() => {
    if (!runActive) return;
    const close = subscribeActivity(
      ticketId,
      (type) => {
        setLiveFeed((f) => [...f.slice(-19), type]);
        void qc.invalidateQueries({ queryKey: ["support-trace", ticketId] });
        onChanged();
      },
      () => {
        /* SSE unavailable — polling covers it */
      },
    );
    return close;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ticketId, runActive]);

  async function onSolve() {
    setSolving(true);
    setError(null);
    setLiveFeed([]);
    try {
      await solveTicket(ticketId);
      onChanged();
      await qc.invalidateQueries({ queryKey: ["support-trace", ticketId] });
    } catch (err) {
      setError(staffApiErrorMessage(err, "AI run failed to start."));
    } finally {
      setSolving(false);
    }
  }

  async function onTakeOver() {
    setTakingOver(true);
    setError(null);
    try {
      await takeOverTicket(ticketId);
      onChanged();
      await qc.invalidateQueries({ queryKey: ["support-trace", ticketId] });
    } catch (err) {
      setError(staffApiErrorMessage(err, "Takeover failed."));
    } finally {
      setTakingOver(false);
    }
  }

  const refreshAll = () => {
    onChanged();
    void qc.invalidateQueries({ queryKey: ["support-trace", ticketId] });
  };

  const pending = (trace.data?.approvals ?? []).filter((a) => a.status === "PENDING");
  const solvable = !["RESOLVED", "CLOSED"].includes(ticketStatus) && !runActive;

  function openSolveInChat() {
    nav(`/chat?new=1&solve=${encodeURIComponent(ticketNumber)}`);
  }

  const intent = trace.data?.run?.intent;
  const workflow = trace.data?.run?.workflow;

  return (
    <Card>
      <div className="ns-row-between">
        <h2 className="flex items-center gap-1.5 text-sm font-semibold">
          <Sparkles size={15} aria-hidden className="text-indigo-600" /> AI Support Copilot
        </h2>
        {runActive ? (
          <Button variant="secondary" disabled={takingOver} onClick={() => void onTakeOver()}>
            {takingOver ? "Taking over…" : "Take over"}
          </Button>
        ) : solvable ? (
          <div className="flex gap-2">
            <Button onClick={openSolveInChat}>Solve in chat</Button>
            <Button variant="secondary" disabled={solving} onClick={() => void onSolve()}>
              {solving ? "Starting…" : "Solve with AI"}
            </Button>
          </div>
        ) : null}
      </div>

      {error ? <p className="mt-2 text-[13px] text-red-600" role="alert">{error}</p> : null}

      {intent ? (
        <p className="mt-2 text-[13px] text-slate-600">
          Intent <span className="font-semibold text-slate-900">{intent}</span>
          {workflow ? (
            <> · workflow <span className="font-semibold text-slate-900">{workflow}</span></>
          ) : null}
        </p>
      ) : null}

      {!trace.data?.run ? (
        <p className="sp-muted mt-2 text-[13px]">
          “Solve with AI” runs the canonical LangGraph here (supervisor → workflow →
          policy → HITL → verify). “Solve in chat” opens a draft instead — nothing runs
          until you send.
        </p>
      ) : (
        <ol className="mt-3 flex flex-col gap-0">
          {(trace.data?.steps ?? []).map((step, i, arr) => (
            <li key={step.key} className="flex gap-2.5">
              <div className="flex flex-col items-center">
                <span className={step.state === "done" ? "text-emerald-600" : step.state === "active" ? "text-indigo-600" : "text-slate-300"}>
                  {step.state === "done" ? (
                    <Check size={16} aria-hidden />
                  ) : step.state === "active" ? (
                    <Loader2 size={16} aria-hidden className="animate-spin" />
                  ) : (
                    <Circle size={16} aria-hidden />
                  )}
                </span>
                {i < arr.length - 1 ? (
                  <span className={`h-4 w-px ${step.state === "done" ? "bg-emerald-200" : "bg-slate-200"}`} aria-hidden />
                ) : null}
              </div>
              <p className={`pb-2.5 text-[13px] ${step.state === "todo" ? "text-slate-400" : "font-medium"}`}>
                {step.label}
                {step.detail ? (
                  <span className="mt-0.5 block font-mono text-xs font-normal text-slate-500">
                    {step.detail}
                  </span>
                ) : null}
              </p>
            </li>
          ))}
        </ol>
      )}

      {runActive && liveFeed.length > 0 ? (
        <p className="mt-2 font-mono text-[11px] text-slate-500" aria-live="polite">
          live: {liveFeed.slice(-5).join(" · ")}
        </p>
      ) : null}

      {pending.map((a) => (
        <div key={a.id} className="mt-2">
          <ApprovalCard approval={a} onDecided={refreshAll} />
        </div>
      ))}

      {(trace.data?.audits ?? []).length > 0 ? (
        <details className="mt-3 rounded-lg bg-slate-50 px-3 py-2">
          <summary className="cursor-pointer text-[13px] font-medium text-slate-600">
            Audit trail ({trace.data?.audits.length})
          </summary>
          <ul className="mt-1.5 flex flex-col gap-1">
            {(trace.data?.audits ?? []).map((a, i) => (
              <li key={`${a.event}-${i}`} className="flex items-center justify-between gap-2 text-xs text-slate-500">
                <span>
                  <span className="font-medium text-slate-700">{a.event.split("_").join(" ")}</span>
                  {" "}· {a.actor.split("_").join(" ").toLowerCase()}
                </span>
                <span className="shrink-0">{new Date(a.at).toLocaleString()}</span>
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </Card>
  );
}
