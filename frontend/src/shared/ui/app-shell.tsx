import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { X } from "lucide-react";
import { Suspense, useCallback, useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { SidebarContent } from "@/shared/ui/sidebar";
import { Topbar } from "@/shared/ui/topbar";
import { ToastProvider } from "@/shared/ui/toast";

/**
 * Route page transition: fade + slide-up on navigation.
 * Skipped entirely under prefers-reduced-motion.
 */
function PageTransition({ children }: { children: React.ReactNode }) {
  const reduce = useReducedMotion();
  if (reduce) return <>{children}</>;
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  );
}

/**
 * Single AppShell for every surface: dark sidebar + topbar + content.
 * Mobile (<lg): hamburger opens a collapsible drawer (AnimatePresence).
 * /ops/login renders bare (no chrome) so sign-in stays centered.
 */
export function AppShell() {
  const [drawer, setDrawer] = useState(false);
  const reduce = useReducedMotion();
  const location = useLocation();
  const isAuth = location.pathname.startsWith("/ops/login");

  const close = useCallback(() => setDrawer(false), []);

  // Close on route change + Escape; lock body scroll while open.
  useEffect(() => {
    close();
  }, [location.pathname, close]);

  useEffect(() => {
    if (!drawer) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
    };
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [drawer, close]);

  if (isAuth) {
    return <Outlet />;
  }

  return (
    <ToastProvider>
      <div className="min-h-screen bg-slate-100 lg:flex">
        {/* Desktop sidebar */}
        <div className="hidden lg:block">
          <aside
            className="sticky top-0 flex h-screen w-[264px] shrink-0"
            style={{ background: "var(--ns-sidebar)" }}
          >
            <div className="flex h-full w-full flex-col">
              <SidebarContent />
            </div>
          </aside>
        </div>

        {/* Mobile drawer */}
        <AnimatePresence>
          {drawer && (
            <div key="drawer" className="fixed inset-0 z-50 lg:hidden">
              <motion.div
                aria-hidden
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={reduce ? { duration: 0 } : { duration: 0.2 }}
                onClick={close}
                className="absolute inset-0 bg-slate-950/50"
              />
              <motion.aside
                role="dialog"
                aria-modal="true"
                aria-label="Navigation"
                initial={reduce ? { opacity: 0 } : { opacity: 0, x: -280 }}
                animate={reduce ? { opacity: 1 } : { opacity: 1, x: 0 }}
                exit={reduce ? { opacity: 0 } : { opacity: 0, x: -280 }}
                transition={reduce ? { duration: 0 } : { type: "tween", duration: 0.25, ease: "easeOut" }}
                className="absolute left-0 top-0 flex h-full w-[280px] flex-col"
                style={{ background: "var(--ns-sidebar)" }}
              >
                <button
                  type="button"
                  onClick={close}
                  aria-label="Close navigation"
                  className="absolute right-2 top-3 rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-900"
                >
                  <X aria-hidden className="h-5 w-5" />
                </button>
                <div className="h-full pt-1">
                  <SidebarContent onNavigate={close} />
                </div>
              </motion.aside>
            </div>
          )}
        </AnimatePresence>

        <div className="min-w-0 flex-1">
          <Topbar onMenu={() => setDrawer(true)} />
          <Suspense fallback={<p className="ns-page text-sm text-slate-500">Loading…</p>}>
            <PageTransition key={location.pathname}>
              <Outlet />
            </PageTransition>
          </Suspense>
        </div>
      </div>
    </ToastProvider>
  );
}
