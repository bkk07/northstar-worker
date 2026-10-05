import { Suspense } from "react";
import { Link, Outlet, useLocation } from "react-router-dom";

const LINKS = [
  ["/evaluation", "Results"],
  ["/evaluation/scenarios", "Scenarios"],
  ["/evaluation/comparison", "Comparison"],
] as const;

export function EvaluationLayout() {
  const location = useLocation();
  return (
    <div className="min-h-screen bg-white text-slate-900">
      <nav aria-label="Evaluation" className="flex gap-4 border-b p-4 text-sm">
        {LINKS.map(([to, label]) => (
          <Link
            key={to}
            to={to}
            aria-current={location.pathname === to ? "page" : undefined}
            className={location.pathname === to ? "font-semibold underline" : "underline"}
          >
            {label}
          </Link>
        ))}
      </nav>
      <Suspense fallback={<p className="p-8 text-sm text-slate-500">Loading evaluation view…</p>}>
        <Outlet />
      </Suspense>
    </div>
  );
}
