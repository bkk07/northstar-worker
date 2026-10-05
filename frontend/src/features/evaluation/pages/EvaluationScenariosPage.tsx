import { useState } from "react";
import { ScenarioTable } from "../scenarios/components/ScenarioTable";

export default function EvaluationScenariosPage() {
  const [suite, setSuite] = useState("seeded");
  return (
    <main className="mx-auto max-w-4xl p-8">
      <h1 className="text-2xl font-semibold">Scenarios</h1>
      <p className="mt-2 text-sm text-slate-600">
        The seeded catalog — and the sealed held-out set — the oracle derives from.
      </p>
      <label className="mt-3 flex items-center gap-2 text-sm">
        Suite
        <select
          value={suite}
          onChange={(event) => setSuite(event.target.value)}
          className="rounded border px-2 py-1"
        >
          <option value="seeded">seeded</option>
          <option value="held_out">held_out</option>
        </select>
      </label>
      <div className="mt-4" key={suite}>
        <ScenarioTable suite={suite} />
      </div>
    </main>
  );
}
