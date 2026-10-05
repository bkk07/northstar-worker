import { RunComparison, SeededVsHeldOut } from "../comparison/components/RunComparison";

export default function EvaluationComparisonPage() {
  return (
    <main className="mx-auto max-w-4xl p-8">
      <h1 className="text-2xl font-semibold">Run comparison</h1>
      <p className="mt-2 text-sm text-slate-600">
        Baseline vs candidate metric ledgers across recorded runs.
      </p>
      <section aria-label="Seeded versus held-out" className="mt-4">
        <h2 className="text-lg font-medium">Seeded vs held-out</h2>
        <div className="mt-2">
          <SeededVsHeldOut />
        </div>
      </section>
      <div className="mt-6">
        <RunComparison />
      </div>
    </main>
  );
}
