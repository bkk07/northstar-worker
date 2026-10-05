import { ErrorState, LoadingState } from "@/shared/ui/feedback";
import { getErrorMessage } from "@/shared/lib/errors";
import { useTaskEvidence, useTaskScreenshots, useTaskVerification } from "../../hooks/useWorker";
import type { EvidencePacketRead, ScreenshotRead, VerificationRead } from "../../types";

export function EvidenceViewer({ taskId }: { taskId: string }) {
  const evidence = useTaskEvidence(taskId);
  const shots = useTaskScreenshots(taskId);
  const verification = useTaskVerification(taskId);
  if (evidence.isPending) return <LoadingState what="evidence" />;
  if (evidence.isError) {
    const status = (evidence.error as { response?: { status?: number } })?.response?.status;
    if (status === 404)
      return (
        <p className="text-sm text-slate-500">No evidence packet yet — the run has not ended.</p>
      );
    return (
      <ErrorState message={getErrorMessage(evidence.error)} onRetry={() => evidence.refetch()} />
    );
  }
  if (!evidence.data) return <LoadingState what="evidence" />;
  return (
    <EvidenceViewerView
      packet={evidence.data}
      screenshots={shots.data ?? []}
      verification={verification.data ?? []}
    />
  );
}

// Split for testability: pure view over packet, screenshots, verdicts.
export function EvidenceViewerView({
  packet,
  screenshots,
  verification,
}: {
  packet: EvidencePacketRead;
  screenshots: ScreenshotRead[];
  verification: VerificationRead[];
}) {
  const body = (packet.packet ?? {}) as Record<string, unknown>;
  const summaryLines = packet.summary.split("\n").filter(Boolean);
  const policy = (body.policy ?? {}) as Record<string, unknown>;
  const decision = (policy.decision ?? {}) as Record<string, unknown>;
  const journal = (body.journal ?? {}) as Record<string, unknown>;
  const memory = (body.memory ?? {}) as Record<string, unknown>;
  const audit = (body.audit ?? {}) as Record<string, unknown>;
  return (
    <div className="flex flex-col gap-4 text-sm">
      <section aria-label="Packet summary">
        <h3 className="font-medium">Summary</h3>
        <ul className="mt-1 flex flex-col gap-1">
          {summaryLines.map((line, index) => (
            <li key={index} className="rounded bg-slate-50 p-2">
              {line}
            </li>
          ))}
        </ul>
      </section>
      <section aria-label="Policy decision">
        <h3 className="font-medium">Policy</h3>
        <p className="mt-1">
          {String(decision.outcome ?? "")} · {String(decision.rule_id ?? "")} —{" "}
          {String(decision.reason ?? "")}
        </p>
      </section>
      <section aria-label="Verification">
        <h3 className="font-medium">Verification</h3>
        {verification.length === 0 ? (
          <p className="mt-1 text-slate-500">No persisted verdicts.</p>
        ) : (
          <ul className="mt-1 flex flex-col gap-1">
            {verification.map((result) => (
              <li key={result.id} className="rounded border p-2">
                <span className="font-medium">{result.verdict}</span>
                <pre className="mt-1 overflow-x-auto text-xs">
                  {JSON.stringify({ invariants: result.invariants, diff: result.diff }, null, 2)}
                </pre>
              </li>
            ))}
          </ul>
        )}
      </section>
      <section aria-label="Recovery">
        <h3 className="font-medium">Recovery</h3>
        <p className="mt-1">
          committed: {(journal.committed as string[] | undefined)?.join(", ") || "none"}
          {journal.recovered === true
            ? ` · recovered from ${String(journal.failure_type ?? "")}`
            : ""}
        </p>
      </section>
      <section aria-label="Memory provenance">
        <h3 className="font-medium">Memory</h3>
        <p className="mt-1">
          {Number(memory.item_count ?? 0)} items ({Number(memory.trust ?? 0)} trusted /{" "}
          {Number(memory.untrusted ?? 0)} untrusted)
        </p>
      </section>
      <section aria-label="Packet screenshots">
        <h3 className="font-medium">Screenshots ({screenshots.length})</h3>
        {screenshots.length === 0 ? (
          <p className="mt-1 text-slate-500">No screenshots captured.</p>
        ) : (
          <ul className="mt-1 flex flex-col gap-1 font-mono text-xs">
            {screenshots.map((shot, index) => (
              <li key={`${shot.run_id}-${shot.label}-${index}`}>
                {shot.label}: {shot.path}
              </li>
            ))}
          </ul>
        )}
      </section>
      <section aria-label="Audit pointer">
        <h3 className="font-medium">Audit</h3>
        <p className="mt-1 text-slate-600">
          {Number(audit.events ?? 0)} events, seq {String(audit.first_seq ?? "?")} →{" "}
          {String(audit.last_seq ?? "?")}
        </p>
      </section>
    </div>
  );
}
