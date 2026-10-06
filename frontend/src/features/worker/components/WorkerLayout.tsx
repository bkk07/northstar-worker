import { Suspense } from "react";
import { Link, Outlet, useLocation } from "react-router-dom";
import { cn } from "@/shared/lib/utils";

const LINKS = [
  ["/worker", "Dashboard"],
  ["/worker/assistant", "Assistant"],
  ["/worker/environment", "Environment"],
] as const;

function isActive(pathname: string, to: string) {
  if (to === "/worker") return pathname === "/worker";
  return pathname === to || pathname.startsWith(`${to}/`);
}

/** Thin pass-through: AppShell owns sidebar/topbar; this keeps worker sub-tabs. */
export function WorkerLayout() {
  const location = useLocation();
  return (
    <div>
      <nav aria-label="Worker" className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex w-full max-w-7xl gap-1 px-4 py-2 sm:px-6 lg:px-8">
          {LINKS.map(([to, label]) => {
            const active = isActive(location.pathname, to);
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
      <Suspense fallback={<p className="ns-page text-sm text-slate-500">Loading worker view…</p>}>
        <Outlet />
      </Suspense>
    </div>
  );
}
