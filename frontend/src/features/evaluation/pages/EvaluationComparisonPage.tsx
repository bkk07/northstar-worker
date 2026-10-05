import { RunComparison } from "../comparison/components/RunComparison";

export default function EvaluationComparisonPage() {
  return (
    <main className="mx-auto max-w-4xl p-8">
      <h1 className="text-2xl font-semibold">Run comparison</h1>
      <p className="mt-2 text-sm text-slate-600">
        Baseline vs candidate metric ledgers across recorded runs.
      </p>
      <div className="mt-4">
        <RunComparison />
      </div>
    </main>
  );
}
