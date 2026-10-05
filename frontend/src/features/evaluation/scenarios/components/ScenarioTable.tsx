import { ErrorState, LoadingState } from "@/shared/ui/feedback";
import { getErrorMessage } from "@/shared/lib/errors";
import { useEvalScenarios } from "../../hooks/useEvaluation";
import type { EvalScenarioRead } from "../../types";

export function ScenarioTable() {
  const scenarios = useEvalScenarios();
  if (scenarios.isPending) return <LoadingState what="scenarios" />;
  if (scenarios.isError)
    return (
      <ErrorState message={getErrorMessage(scenarios.error)} onRetry={() => scenarios.refetch()} />
    );
  return <ScenarioTableView scenarios={scenarios.data ?? []} />;
}

// Split for testability: pure view over catalog rows.
export function ScenarioTableView({ scenarios }: { scenarios: EvalScenarioRead[] }) {
  if (scenarios.length === 0) return <p className="text-sm text-slate-500">No scenarios.</p>;
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left text-slate-500">
          <th>ID</th>
          <th>Category</th>
          <th>Ticket</th>
          <th>Task</th>
          <th>Expected</th>
        </tr>
      </thead>
      <tbody>
        {scenarios.map((scenario) => (
          <tr key={scenario.id} className="border-t align-top">
            <td className="font-mono">{scenario.id}</td>
            <td>{scenario.category}</td>
            <td className="font-mono">{scenario.ticket_code}</td>
            <td className="max-w-md">{scenario.task}</td>
            <td>
              <span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs font-medium">
                {scenario.expected_outcome}
              </span>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
