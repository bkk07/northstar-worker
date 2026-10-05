import { LatestResults } from "../results/components/RunResults";

export default function EvaluationResultsPage() {
  return (
    <main className="mx-auto max-w-4xl p-8">
      <h1 className="text-2xl font-semibold">Evaluation</h1>
      <p className="mt-2 text-sm text-slate-600">
        Latest recorded suite run with the §26 metrics table and per-scenario drilldown.
      </p>
      <div className="mt-4">
        <LatestResults />
      </div>
    </main>
  );
}
