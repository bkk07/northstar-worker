import { useState } from "react";
import { ErrorState, LoadingState } from "@/shared/ui/feedback";
import { getErrorMessage } from "@/shared/lib/errors";
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
export function ApprovalQueueView({ approvals }: { approvals: ApprovalRead[] }) {
  const decided = useDecideApproval();
  const [approver, setApprover] = useState("duty-ops");
  if (approvals.length === 0)
    return <p className="text-sm text-slate-500">No approvals waiting.</p>;
  return (
    <div className="flex flex-col gap-3">
      <label className="flex items-center gap-2 text-sm">
        Approver
        <input
          value={approver}
          onChange={(event) => setApprover(event.target.value)}
          className="rounded border px-2 py-1"
        />
      </label>
      {approvals.map((approval) => (
        <article
          key={approval.id}
          aria-label={`Approval ${approval.id}`}
          className="rounded border p-3 text-sm"
        >
          <p className="font-medium">
            {approval.requested_action}{" "}
            <span className="text-slate-500">· {approval.policy_rule_id}</span>
          </p>
          <p className="mt-1 text-slate-600">{approval.reason}</p>
          <pre className="mt-2 overflow-x-auto rounded bg-slate-50 p-2 text-xs">
            {JSON.stringify(approval.params, null, 2)}
          </pre>
          <div className="mt-2 flex gap-2">
            <button
              type="button"
              disabled={decided.isPending}
              onClick={() =>
                decided.mutate({ approvalId: approval.id, decision: "approve", approver })
              }
              className="rounded bg-green-700 px-3 py-1 text-white disabled:opacity-50"
            >
              Approve
            </button>
            <button
              type="button"
              disabled={decided.isPending}
              onClick={() =>
                decided.mutate({ approvalId: approval.id, decision: "reject", approver })
              }
              className="rounded bg-red-700 px-3 py-1 text-white disabled:opacity-50"
            >
              Reject
            </button>
          </div>
        </article>
      ))}
      {decided.isError && (
        <p role="alert" className="text-sm text-red-700">
          {getErrorMessage(decided.error)}
        </p>
      )}
      {decided.isSuccess && (
        <p className="text-sm text-green-700">Decision recorded; the task requeued.</p>
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
    return <p className="text-sm text-slate-500">No questions waiting.</p>;
  return (
    <div className="flex flex-col gap-3">
      {clarifications.map((item) => (
        <article
          key={item.id}
          aria-label={`Clarification ${item.id}`}
          className="rounded border p-3 text-sm"
        >
          <p className="font-medium">
            {item.kind} <span className="text-slate-500">· task {item.task_id.slice(0, 8)}</span>
          </p>
          <p className="mt-1">{item.question}</p>
          <form
            aria-label={`Answer ${item.id}`}
            className="mt-2 flex gap-2"
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
              className="flex-1 rounded border px-2 py-1"
            />
            <button
              type="submit"
              disabled={answered.isPending}
              className="rounded bg-slate-900 px-3 py-1 text-white disabled:opacity-50"
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
        <p className="text-sm text-green-700">Answer recorded; the task requeued.</p>
      )}
    </div>
  );
}
