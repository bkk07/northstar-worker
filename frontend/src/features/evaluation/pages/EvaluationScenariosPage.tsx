import { ScenarioTable } from "../scenarios/components/ScenarioTable";

export default function EvaluationScenariosPage() {
  return (
    <main className="mx-auto max-w-4xl p-8">
      <h1 className="text-2xl font-semibold">Scenarios</h1>
      <p className="mt-2 text-sm text-slate-600">
        The seeded catalog — the same file the oracle derives expectations from.
      </p>
      <div className="mt-4">
        <ScenarioTable />
      </div>
    </main>
  );
}
