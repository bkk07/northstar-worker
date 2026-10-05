import { ErrorState, LoadingState } from "@/shared/ui/feedback";
import { getErrorMessage } from "@/shared/lib/errors";
import { useEvalRun, useEvalRuns } from "../../hooks/useEvaluation";
import { METRIC_TARGETS, formatMetricValue, type EvalRunDetail } from "../../types";

export function LatestResults() {
  const runs = useEvalRuns(1);
  if (runs.isPending) return <LoadingState what="evaluation runs" />;
  if (runs.isError)
    return <ErrorState message={getErrorMessage(runs.error)} onRetry={() => runs.refetch()} />;
  const latest = (runs.data ?? [])[0];
  if (!latest) return <p className="text-sm text-slate-500">No evaluation runs recorded.</p>;
  return <RunResults runId={latest.id} />;
}

export function RunResults({ runId }: { runId: string }) {
  const detail = useEvalRun(runId);
  if (detail.isPending) return <LoadingState what="evaluation run" />;
  if (detail.isError)
    return <ErrorState message={getErrorMessage(detail.error)} onRetry={() => detail.refetch()} />;
  if (!detail.data) return <LoadingState what="evaluation run" />;
  return <RunResultsView detail={detail.data} />;
}

// Split for testability: pure view over one recorded run.
export function RunResultsView({ detail }: { detail: EvalRunDetail }) {
  const { run, results } = detail;
  return (
    <div className="flex flex-col gap-4 text-sm">
      <p className="text-slate-600">
        {run.suite} · {run.scenario_count} scenarios · {new Date(run.created_at).toLocaleString()}
      </p>
      <section aria-label="Metrics">
        <h3 className="font-medium">Metrics (§26)</h3>
        <table className="mt-2 w-full">
          <thead>
            <tr className="text-left text-slate-500">
              <th>Metric</th>
              <th>Result</th>
              <th>Target</th>
            </tr>
          </thead>
          <tbody>
            {METRIC_TARGETS.map(([metric, target]) => (
              <tr key={metric} className="border-t">
                <td className="font-mono text-xs">{metric}</td>
                <td className="font-medium">{formatMetricValue(run.metrics[metric])}</td>
                <td className="text-slate-500">{target}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <section aria-label="Per-scenario drilldown">
        <h3 className="font-medium">Scenarios</h3>
        <ul className="mt-2 flex flex-col gap-1">
          {results.map((result) => (
            <li key={result.id} className="flex items-center gap-2 rounded border p-2">
              <span aria-label={result.outcome_ok ? "pass" : "fail"}>
                {result.outcome_ok ? "✓" : "✗"}
              </span>
              <span className="font-mono">{result.scenario_id}</span>
              <span className="text-slate-500">
                expected {result.expected_outcome}, got {result.actual_outcome}
              </span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
