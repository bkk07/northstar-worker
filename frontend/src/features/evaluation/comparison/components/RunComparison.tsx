import { useState } from "react";
import { ErrorState, LoadingState } from "@/shared/ui/feedback";
import { getErrorMessage } from "@/shared/lib/errors";
import { useEvalRuns } from "../../hooks/useEvaluation";
import { METRIC_TARGETS, formatMetricValue } from "../../types";

export function SeededVsHeldOut() {
  const runs = useEvalRuns(50);
  if (runs.isPending) return <LoadingState what="evaluation runs" />;
  if (runs.isError)
    return <ErrorState message={getErrorMessage(runs.error)} onRetry={() => runs.refetch()} />;
  const options = runs.data ?? [];
  const latest = (prefix: string) => options.find((run) => run.suite.startsWith(prefix));
  const seeded = latest("seeded");
  const heldOut = latest("held-out") ?? latest("held_out");
  if (!seeded || !heldOut)
    return <p className="text-sm text-slate-500">Need one seeded and one held-out run.</p>;
  return (
    <div>
      <p className="text-sm text-slate-600">
        {seeded.suite} vs {heldOut.suite}
      </p>
      <div className="mt-2">
        <RunComparisonView left={seeded.metrics} right={heldOut.metrics} />
      </div>
    </div>
  );
}

export function RunComparison() {
  const runs = useEvalRuns(20);
  const [leftId, setLeftId] = useState("");
  const [rightId, setRightId] = useState("");
  if (runs.isPending) return <LoadingState what="evaluation runs" />;
  if (runs.isError)
    return <ErrorState message={getErrorMessage(runs.error)} onRetry={() => runs.refetch()} />;
  const options = runs.data ?? [];
  const left = options.find((run) => run.id === leftId);
  const right = options.find((run) => run.id === rightId);
  return (
    <div className="flex flex-col gap-3 text-sm">
      <div className="flex flex-wrap gap-2">
        <label className="flex items-center gap-2">
          Baseline
          <select
            value={leftId}
            onChange={(event) => setLeftId(event.target.value)}
            className="rounded border px-2 py-1"
          >
            <option value="">—</option>
            {options.map((run) => (
              <option key={run.id} value={run.id}>
                {run.suite} · {new Date(run.created_at).toLocaleString()}
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-2">
          Candidate
          <select
            value={rightId}
            onChange={(event) => setRightId(event.target.value)}
            className="rounded border px-2 py-1"
          >
            <option value="">—</option>
            {options.map((run) => (
              <option key={run.id} value={run.id}>
                {run.suite} · {new Date(run.created_at).toLocaleString()}
              </option>
            ))}
          </select>
        </label>
      </div>
      {left && right && <RunComparisonView left={left.metrics} right={right.metrics} />}
    </div>
  );
}

// Split for testability: pure delta table over two metric ledgers.
export function RunComparisonView({
  left,
  right,
}: {
  left: Record<string, number | null>;
  right: Record<string, number | null>;
}) {
  return (
    <table className="w-full">
      <thead>
        <tr className="text-left text-slate-500">
          <th>Metric</th>
          <th>Baseline</th>
          <th>Candidate</th>
          <th>Δ</th>
        </tr>
      </thead>
      <tbody>
        {METRIC_TARGETS.map(([metric]) => (
          <tr key={metric} className="border-t">
            <td className="font-mono text-xs">{metric}</td>
            <td>{formatMetricValue(left[metric])}</td>
            <td>{formatMetricValue(right[metric])}</td>
            <td>{deltaCell(left[metric], right[metric])}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function deltaCell(
  left: number | null | undefined,
  right: number | null | undefined,
): string {
  if (left === null || left === undefined || right === null || right === undefined) return "n/a";
  const delta = right - left;
  const sign = delta >= 0 ? "+" : "";
  return `${sign}${delta.toFixed(3)}`;
}
