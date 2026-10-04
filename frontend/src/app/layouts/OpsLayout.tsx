import { Suspense, useEffect } from "react";
import { Link, Outlet, useNavigate } from "react-router-dom";
import { ToastProvider } from "@/shared/ui/toast";
import { installOpsAuthInterceptor } from "@/features/ops/api/interceptor";
import { useLogout } from "@/features/ops/auth/hooks/useAuth";

// Authenticated console shell: section nav, logout, toasts, 401 handling.
export function OpsLayout() {
  const navigate = useNavigate();
  const logout = useLogout(() => navigate("/ops/login"));

  useEffect(() => {
    installOpsAuthInterceptor();
  }, []);

  return (
    <ToastProvider>
      <div className="min-h-screen bg-white text-slate-900">
        <nav className="flex items-center gap-4 border-b p-4 text-sm" aria-label="Ops">
          <span className="font-semibold">Ops Console</span>
          <Link to="/ops/tickets">Tickets</Link>
          <Link to="/ops/customers">Customers</Link>
          <Link to="/ops/orders">Orders</Link>
          <button
            type="button"
            onClick={() => logout.mutate()}
            className="ml-auto underline"
            aria-label="Log out"
          >
            Log out
          </button>
        </nav>
        <Suspense fallback={<p className="p-8 text-sm">Loading…</p>}>
          <Outlet />
        </Suspense>
      </div>
    </ToastProvider>
  );
}

// Unauthenticated shell for the login page (no console nav).
export function OpsAuthLayout() {
  useEffect(() => {
    installOpsAuthInterceptor();
  }, []);

  return (
    <ToastProvider>
      <div className="min-h-screen bg-white text-slate-900">
        <Suspense fallback={<p className="p-8 text-sm">Loading…</p>}>
          <Outlet />
        </Suspense>
      </div>
    </ToastProvider>
  );
}
