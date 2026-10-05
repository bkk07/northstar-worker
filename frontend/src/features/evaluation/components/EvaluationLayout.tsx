import { Suspense } from "react";
import { Link, Outlet, useLocation } from "react-router-dom";
import { cn } from "@/shared/lib/utils";

const LINKS = [
  ["/evaluation", "Results"],
  ["/evaluation/scenarios", "Scenarios"],
  ["/evaluation/comparison", "Comparison"],
] as const;

/** Thin pass-through: AppShell owns sidebar/topbar; this keeps evaluation sub-tabs. */
export function EvaluationLayout() {
  const location = useLocation();
  return (
    <div>
      <nav aria-label="Evaluation" className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex w-full max-w-7xl gap-1 px-4 py-2 sm:px-6 lg:px-8">
          {LINKS.map(([to, label]) => {
            const active = location.pathname === to;
            return (
              <Link
                key={to}
                to={to}
                aria-current={active ? "page" : undefined}
                className={cn("ns-tab", active && "ns-tab-active")}
              >
                {label}
              </Link>
            );
          })}
        </div>
      </nav>
      <Suspense fallback={<p className="ns-page text-sm text-slate-500">Loading evaluation view…</p>}>
        <Outlet />
      </Suspense>
    </div>
  );
}
