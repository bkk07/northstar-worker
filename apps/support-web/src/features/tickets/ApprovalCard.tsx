import { useState } from "react";
import { Button, Input } from "@/components/ui";
import { staffApiErrorMessage } from "@/lib/api-client";
import { decideApproval, type TraceApproval } from "@/services/support-api";

function formatPaise(paise: number | null | undefined): string {
  if (paise == null) return "—";
  return `₹${Math.floor(paise / 100).toLocaleString("en-IN")}`;
}

function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-IN", {
    day: "numeric",
    month: "short",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function ApprovalCard({
  approval,
  onDecided,
}: {
  approval: TraceApproval;
  onDecided: () => void;
}) {
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState<"approve" | "reject" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const payload = approval.action_payload as {
    order_id?: string;
    amount_paise?: number | null;
    reason?: string;
  };

  async function decide(approved: boolean) {
    setBusy(approved ? "approve" : "reject");
    setError(null);
    try {
      await decideApproval(approval.id, approved, note.trim() || undefined);
      onDecided();
    } catch (err) {
      setError(staffApiErrorMessage(err, "Decision failed. Please try again."));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="rounded-xl border border-amber-300 bg-amber-50 p-3">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-semibold text-amber-900">Approval required</p>
        {approval.expires_at ? (
          <p className="text-xs text-amber-700">Expires {formatDate(approval.expires_at)}</p>
        ) : null}
      </div>
      <dl className="mt-1.5 flex flex-col gap-0.5 text-[13px] text-slate-700">
        <div className="flex gap-1.5"><dt className="sp-muted">Action</dt><dd className="font-semibold">{approval.action_type}</dd></div>
        <div className="flex gap-1.5"><dt className="sp-muted">Amount</dt><dd className="font-semibold">{formatPaise(payload.amount_paise)}</dd></div>
        {payload.order_id ? (
          <div className="flex gap-1.5"><dt className="sp-muted">Order</dt><dd className="font-mono text-xs">{payload.order_id.slice(0, 8)}…</dd></div>
        ) : null}
        {payload.reason ? (
          <div className="flex gap-1.5"><dt className="sp-muted">Policy result</dt><dd>{payload.reason}</dd></div>
        ) : null}
        <details className="mt-1">
          <summary className="cursor-pointer text-xs font-medium text-slate-500">Full action payload</summary>
          <pre className="mt-1 overflow-x-auto rounded bg-white p-2 font-mono text-[11px] text-slate-600">
            {JSON.stringify(approval.action_payload, null, 2)}
          </pre>
        </details>
      </dl>
      <Input
        className="mt-2"
        placeholder="Human note (optional)…"
        value={note}
        onChange={(e) => setNote(e.target.value)}
        aria-label="Human note for approval decision"
      />
      {error ? <p className="mt-1.5 text-[13px] text-red-600" role="alert">{error}</p> : null}
      <div className="mt-2 flex gap-2">
        <Button variant="secondary" disabled={busy !== null} onClick={() => void decide(false)}>
          {busy === "reject" ? "Rejecting…" : "Reject"}
        </Button>
        <Button disabled={busy !== null} onClick={() => void decide(true)}>
          {busy === "approve" ? "Approving…" : "Approve"}
        </Button>
      </div>
    </div>
  );
}
