import { EnvironmentPanel } from "../environment/components/EnvironmentPanel";

export default function WorkerEnvironmentPage() {
  return (
    <main className="mx-auto max-w-4xl p-8">
      <h1 className="text-2xl font-semibold">Environment</h1>
      <p className="mt-2 text-sm text-slate-600">
        Faults, world reset, and seeding for demos. Guarded by the ops-session cookie — the operator
        token never reaches the browser.
      </p>
      <div className="mt-4">
        <EnvironmentPanel />
      </div>
    </main>
  );
}
