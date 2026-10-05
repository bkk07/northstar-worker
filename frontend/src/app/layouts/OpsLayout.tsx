import { Suspense, useEffect } from "react";
import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import { LogOut } from "lucide-react";
import { ToastProvider } from "@/shared/ui/toast";
import { installOpsAuthInterceptor } from "@/features/ops/api/interceptor";
import { useLogout } from "@/features/ops/auth/hooks/useAuth";
import { cn } from "@/shared/lib/utils";

const TABS: Array<readonly [string, string]> = [
  ["/ops/tickets", "Tickets"],
  ["/ops/customers", "Customers"],
  ["/ops/orders", "Orders"],
];

/** Thin pass-through: AppShell owns sidebar/topbar; this keeps ops tabs + auth. */
export function OpsLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const logout = useLogout(() => navigate("/ops/login"));

  useEffect(() => {
    installOpsAuthInterceptor();
  }, []);

  return (
    <div>
      <nav aria-label="Ops" className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex w-full max-w-7xl items-center gap-1 px-4 py-2 sm:px-6 lg:px-8">
          {TABS.map(([to, label]) => {
            const active =
              to === "/ops/tickets"
                ? location.pathname.startsWith("/ops/tickets")
                : location.pathname.startsWith(to);
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
          <button
            type="button"
            onClick={() => logout.mutate()}
            aria-label="Log out"
            className="ns-btn ns-btn-ghost ns-btn-sm ml-auto"
          >
            <LogOut aria-hidden className="h-3.5 w-3.5" />
            Log out
          </button>
        </div>
      </nav>
      <Suspense fallback={<p className="ns-page text-sm text-slate-500">Loading…</p>}>
        <Outlet />
      </Suspense>
    </div>
  );
}

export function OpsAuthLayout() {
  useEffect(() => {
    installOpsAuthInterceptor();
  }, []);

  return (
    <ToastProvider>
      <div className="flex min-h-screen items-center justify-center bg-slate-100 p-4">
        <div className="w-full max-w-md">
          <div className="mb-4 text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.1em] text-brand-600">
              Northstar Commerce
            </p>
            <h1 className="mt-1 text-xl font-semibold tracking-tight">Ops Console sign in</h1>
          </div>
          <Suspense fallback={<p className="text-center text-sm text-slate-500">Loading…</p>}>
            <Outlet />
          </Suspense>
        </div>
      </div>
    </ToastProvider>
  );
}
