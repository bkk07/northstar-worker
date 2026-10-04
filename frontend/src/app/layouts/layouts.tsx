import { Outlet } from "react-router-dom";

function Shell({ title, hint }: { title: string; hint: string }) {
  return (
    <main className="mx-auto max-w-3xl p-8">
      <h1 className="text-2xl font-semibold">{title}</h1>
      <p className="mt-2 text-sm text-slate-600">{hint}</p>
      <p className="mt-4 rounded-md bg-slate-100 p-3 text-xs text-slate-500">
        Phase 1 placeholder shell — real UI arrives in its feature phase.
      </p>
    </main>
  );
}

export function RootLayout() {
  return (
    <div className="min-h-screen bg-white text-slate-900">
      <nav className="flex gap-4 border-b p-4 text-sm">
        <a href="/shop">Shop</a>
        <a href="/ops">Ops</a>
        <a href="/worker">Worker</a>
        <a href="/evaluation">Evaluation</a>
      </nav>
      <Outlet />
    </div>
  );
}

export function WorkerLayout() {
  return (
    <Shell
      title="Worker Control Center"
      hint="Tasks, timeline, approvals, evidence, memory, environment (Phase 26)."
    />
  );
}

export function EvaluationLayout() {
  return <Shell title="Evaluation" hint="Seeded vs held-out metrics and drilldowns (Phase 27)." />;
}
