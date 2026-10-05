import { motion, useReducedMotion, type PanInfo } from "framer-motion";
import { useState } from "react";
import { Check, MessageCircleQuestion, ShieldCheck, X } from "lucide-react";
import { ErrorState, LoadingState } from "@/shared/ui/feedback";
import { EmptyState } from "@/shared/ui/empty-state";
import { getErrorMessage } from "@/shared/lib/errors";
import { Badge } from "@/shared/ui/badge";
import {
  useAnswerClarification,
  useApprovals,
  useClarifications,
  useDecideApproval,
} from "../../hooks/useWorker";
import type { ApprovalRead, ClarificationRead } from "../../types";

export function ApprovalQueue() {
  const approvals = useApprovals();
  if (approvals.isPending) return <LoadingState what="approvals" />;
  if (approvals.isError)
    return (
      <ErrorState message={getErrorMessage(approvals.error)} onRetry={() => approvals.refetch()} />
    );
  return <ApprovalQueueView approvals={approvals.data ?? []} />;
}

// Split for testability: pure view over the pending approvals.
// Cards swipe right to approve, left to reject (buttons always available).
export function ApprovalQueueView({ approvals }: { approvals: ApprovalRead[] }) {
  const decided = useDecideApproval();
  const [approver, setApprover] = useState("duty-ops");
  const reduce = useReducedMotion();
  if (approvals.length === 0)
    return (
      <EmptyState
        title="No approvals waiting."
        desc="Sensitive actions pause here for an operator decision."
        icon={ShieldCheck}
      />
    );

  function decide(approvalId: string, decision: "approve" | "reject") {
    if (decided.isPending) return;
    decided.mutate({ approvalId, decision, approver });
  }

  function onDragEnd(approvalId: string) {
    return (_: unknown, info: PanInfo) => {
      if (info.offset.x > 90) decide(approvalId, "approve");
      else if (info.offset.x < -90) decide(approvalId, "reject");
    };
  }

  return (
    <div className="flex flex-col gap-3">
      <label className="flex max-w-xs items-center gap-2 text-[13px] text-slate-600">
        <span className="shrink-0 font-medium">Approver</span>
        <input
          value={approver}
          onChange={(event) => setApprover(event.target.value)}
          className="ns-input"
        />
      </label>
      <p className="text-xs text-slate-400">Tip: swipe a card right to approve, left to reject.</p>
      {approvals.map((approval) => (
        <motion.article
          key={approval.id}
          aria-label={`Approval ${approval.id}`}
          drag={reduce ? false : "x"}
          dragConstraints={{ left: 0, right: 0 }}
          dragElastic={0.6}
          onDragEnd={onDragEnd(approval.id)}
          whileDrag={{ scale: 1.02 }}
          className="rounded-2xl border border-amber-200 bg-amber-50/40 p-3.5 text-sm"
        >
          <div className="flex flex-wrap items-center gap-2">
            <p className="font-semibold">{approval.requested_action}</p>
            <Badge tone="human_approval">{approval.policy_rule_id}</Badge>
          </div>
          <p className="mt-1 text-[13px] leading-5 text-slate-600">{approval.reason}</p>
          <pre className="mt-2 overflow-x-auto rounded-xl border border-slate-200 bg-slate-950 p-2.5 font-mono text-[11px] leading-5 text-slate-100">
            {JSON.stringify(approval.params, null, 2)}
          </pre>
          <div className="mt-2.5 flex gap-2">
            <motion.button
              type="button"
              disabled={decided.isPending}
              onClick={() => decide(approval.id, "approve")}
              whileTap={reduce ? undefined : { scale: 0.97 }}
              className="ns-btn ns-btn-success ns-btn-sm"
            >
              <Check aria-hidden className="h-3.5 w-3.5" />
              Approve
            </motion.button>
            <motion.button
              type="button"
              disabled={decided.isPending}
              onClick={() => decide(approval.id, "reject")}
              whileTap={reduce ? undefined : { scale: 0.97 }}
              className="ns-btn ns-btn-danger ns-btn-sm"
            >
              <X aria-hidden className="h-3.5 w-3.5" />
              Reject
            </motion.button>
          </div>
        </motion.article>
      ))}
      {decided.isError && (
        <p role="alert" className="text-sm text-red-700">
          {getErrorMessage(decided.error)}
        </p>
      )}
      {decided.isSuccess && (
        <p role="status" className="text-[13px] font-medium text-emerald-700">
          Decision recorded; the task requeued.
        </p>
      )}
    </div>
  );
}

export function ClarificationQueue() {
  const clarifications = useClarifications();
  if (clarifications.isPending) return <LoadingState what="clarifications" />;
  if (clarifications.isError)
    return (
      <ErrorState
        message={getErrorMessage(clarifications.error)}
        onRetry={() => clarifications.refetch()}
      />
    );
  return <ClarificationQueueView clarifications={clarifications.data ?? []} />;
}

export function ClarificationQueueView({
  clarifications,
}: {
  clarifications: ClarificationRead[];
}) {
  const answered = useAnswerClarification();
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  if (clarifications.length === 0)
    return (
      <EmptyState
        title="No questions waiting."
        desc="Ambiguous tasks land here for a clarifying answer."
        icon={MessageCircleQuestion}
      />
    );
  return (
    <div className="flex flex-col gap-3">
      {clarifications.map((item) => (
        <article
          key={item.id}
          aria-label={`Clarification ${item.id}`}
          className="rounded-2xl border border-slate-200 bg-white p-3.5 text-sm shadow-sm"
        >
          <p className="flex flex-wrap items-center gap-2 font-medium">
            {item.kind}
            <span className="font-mono text-xs font-normal text-slate-400">
              task {item.task_id.slice(0, 8)}
            </span>
          </p>
          <p className="mt-1 text-[13px]">{item.question}</p>
          <form
            aria-label={`Answer ${item.id}`}
            className="mt-2.5 flex gap-2"
            onSubmit={(event) => {
              event.preventDefault();
              const answer = (drafts[item.id] ?? "").trim();
              if (!answer) return;
              answered.mutate({
                clarificationId: item.id,
                answer,
                answeredBy: "duty-ops",
              });
            }}
          >
            <label htmlFor={`answer-${item.id}`} className="sr-only">
              Answer
            </label>
            <input
              id={`answer-${item.id}`}
              value={drafts[item.id] ?? ""}
              onChange={(event) => setDrafts({ ...drafts, [item.id]: event.target.value })}
              placeholder="Type the answer…"
              className="ns-input flex-1"
            />
            <button
              type="submit"
              disabled={answered.isPending}
              className="ns-btn ns-btn-primary ns-btn-sm shrink-0"
            >
              Answer
            </button>
          </form>
        </article>
      ))}
      {answered.isError && (
        <p role="alert" className="text-sm text-red-700">
          {getErrorMessage(answered.error)}
        </p>
      )}
      {answered.isSuccess && (
        <p role="status" className="text-[13px] font-medium text-emerald-700">
          Answer recorded; the task requeued.
        </p>
      )}
    </div>
  );
}
