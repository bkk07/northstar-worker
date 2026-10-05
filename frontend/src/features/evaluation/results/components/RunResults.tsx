import { Link } from "react-router-dom";
import { BarChart3 } from "lucide-react";
import { ErrorState, LoadingState } from "@/shared/ui/feedback";
import { EmptyState } from "@/shared/ui/empty-state";
import { getErrorMessage } from "@/shared/lib/errors";
import { Card, CardBody, CardHeader } from "@/shared/ui/card";
import { useEvalRun, useEvalRuns } from "../../hooks/useEvaluation";
import { METRIC_TARGETS, formatMetricValue, type EvalRunDetail } from "../../types";

export function LatestResults() {
  const runs = useEvalRuns(1);
  if (runs.isPending) return <LoadingState what="evaluation runs" />;
  if (runs.isError)
    return <ErrorState message={getErrorMessage(runs.error)} onRetry={() => runs.refetch()} />;
  const latest = (runs.data ?? [])[0];
  if (!latest)
    return (
      <EmptyState
        title="No evaluation runs recorded"
        desc="Run python eval/eval.py --suite seeded to produce the first §26 metrics table."
        icon={BarChart3}
        action={
          <Link to="/evaluation/scenarios" className="ns-btn ns-btn-secondary ns-btn-sm">
            Browse scenarios
          </Link>
        }
      />
    );
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
    <div className="space-y-5">
      <p className="text-[13px] text-slate-500">
        <span className="font-semibold text-slate-700">{run.suite}</span> ·{" "}
        {run.scenario_count} scenarios · {new Date(run.created_at).toLocaleString()}
      </p>
      <Card>
        <CardHeader title="Metrics (§26)" desc="Result vs target. Safety rows must be zero." />
        <CardBody className="p-0">
          <div className="ns-table-wrap !rounded-none !border-0 !shadow-none">
            <table className="ns-table">
              <thead>
                <tr>
                  <th scope="col">Metric</th>
                  <th scope="col">Result</th>
                  <th scope="col" className="text-right">
                    Target
                  </th>
                </tr>
              </thead>
              <tbody>
                {METRIC_TARGETS.map(([metric, target]) => (
                  <tr key={metric}>
                    <td className="font-mono text-xs text-slate-600">{metric}</td>
                    <td className="font-semibold tabular-nums">
                      {formatMetricValue(run.metrics[metric])}
                    </td>
                    <td className="text-right text-slate-500">{target}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardBody>
      </Card>
      <Card>
        <CardHeader
          title="Per-scenario drilldown"
          desc="Expected vs actual outcome. Failures link back to task evidence."
        />
        <CardBody>
          <ul className="space-y-2">
            {results.map((result) => (
              <li
                key={result.id}
                className="flex flex-wrap items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-[13px]"
              >
                <span
                  aria-label={result.outcome_ok ? "pass" : "fail"}
                  className={`ns-badge ${result.outcome_ok ? "border-emerald-200 bg-emerald-50 text-emerald-800" : "border-red-200 bg-red-50 text-red-800"}`}
                >
                  {result.outcome_ok ? "✓ pass" : "✗ fail"}
                </span>
                <span className="font-mono text-xs font-medium">{result.scenario_id}</span>
                <span className="text-slate-500">
                  expected {result.expected_outcome}, got {result.actual_outcome}
                </span>
              </li>
            ))}
          </ul>
        </CardBody>
      </Card>
    </div>
  );
}
