import { Suspense } from "react";
import { Outlet } from "react-router-dom";

/** Thin pass-through: AppShell owns sidebar/topbar; shop has no sub-tabs. */
export function ShopLayout() {
  return (
    <Suspense fallback={<p className="ns-page text-sm text-slate-500">Loading…</p>}>
      <Outlet />
    </Suspense>
  );
}
