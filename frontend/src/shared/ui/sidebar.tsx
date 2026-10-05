import { BarChart3, Bot, LifeBuoy, Search, ShoppingBag, type LucideIcon } from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import { cn } from "@/shared/lib/utils";

export type SideLink = {
  to: string;
  label: string;
  desc: string;
  match: string;
  icon: LucideIcon;
};

export const SIDE_LINKS: SideLink[] = [
  { to: "/shop/orders", label: "Shop", desc: "Customer orders", match: "/shop", icon: ShoppingBag },
  { to: "/ops/tickets", label: "Ops Console", desc: "Support queue", match: "/ops", icon: LifeBuoy },
  { to: "/worker", label: "Worker", desc: "Control center", match: "/worker", icon: Bot },
  {
    to: "/evaluation",
    label: "Evaluation",
    desc: "Quality & safety",
    match: "/evaluation",
    icon: BarChart3,
  },
];

export function isSideActive(pathname: string, match: string) {
  return pathname === match || pathname.startsWith(`${match}/`);
}

/** Shared sidebar body: logo, search (visual), nav, user. Used by desktop + mobile drawer. */
export function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const location = useLocation();
  return (
    <div className="flex h-full flex-col text-white">
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 pb-4 pt-6">
        <div
          aria-hidden
          className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-600 text-sm font-bold shadow-lg"
        >
          N
        </div>
        <div className="min-w-0">
          <p className="truncate text-[15px] font-semibold tracking-tight">Northstar</p>
          <p className="text-xs text-slate-400">Operations Worker</p>
        </div>
        <span className="ml-auto rounded-full border border-white/15 bg-white/5 px-2 py-0.5 text-[11px] font-medium text-slate-300">
          v0.1
        </span>
      </div>

      {/* Search — visual only (no palette wired yet) */}
      <div className="px-3 pb-4">
        <button
          type="button"
          aria-label="Search (visual only)"
          title="Search (visual only)"
          onClick={() => {}}
          className="flex w-full items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-[13px] text-slate-400 transition-colors hover:bg-white/10 hover:text-slate-200"
        >
          <Search aria-hidden className="h-4 w-4 shrink-0" />
          <span className="flex-1 truncate text-left">Search…</span>
          <kbd className="rounded border border-white/15 bg-white/5 px-1.5 py-0.5 font-mono text-[10px] text-slate-400">
            ⌘K
          </kbd>
        </button>
      </div>

      {/* Nav — exactly the four surfaces */}
      <nav aria-label="Primary" className="flex-1 overflow-y-auto px-3 pb-4">
        <ul className="space-y-1">
          {SIDE_LINKS.map((link) => {
            const active = isSideActive(location.pathname, link.match);
            const Icon = link.icon;
            return (
              <li key={link.to}>
                <Link
                  to={link.to}
                  aria-current={active ? "page" : undefined}
                  onClick={onNavigate}
                  className={cn("ns-side-link", active && "ns-side-link-active")}
                >
                  <Icon
                    aria-hidden
                    className={cn(
                      "h-4 w-4 shrink-0",
                      active ? "text-indigo-300" : "text-slate-500",
                    )}
                  />
                  <span className="min-w-0">
                    <span className="block truncate leading-5">{link.label}</span>
                    <span
                      className={cn(
                        "block truncate text-xs font-normal",
                        active ? "text-slate-300" : "text-slate-500",
                      )}
                    >
                      {link.desc}
                    </span>
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* User avatar bottom */}
      <div className="border-t border-white/10 p-3">
        <div className="flex items-center gap-2.5 rounded-xl px-2 py-2">
          <span
            aria-hidden
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-xs font-semibold text-white"
          >
            OP
          </span>
          <span className="min-w-0 flex-1">
            <span className="block truncate text-[13px] font-medium text-slate-100">Operator</span>
            <span className="block truncate text-xs text-slate-500">Duty ops · sandbox</span>
          </span>
          <span
            aria-hidden
            className="h-2 w-2 shrink-0 rounded-full bg-emerald-400"
            title="Available"
          />
        </div>
      </div>
    </div>
  );
}

/** Desktop sidebar (hidden below lg). Mobile uses the drawer in AppShell. */
export function Sidebar() {
  return (
    <aside
      className="hidden shrink-0 lg:sticky lg:top-0 lg:flex lg:h-screen lg:w-[264px]"
      style={{ background: "var(--ns-sidebar)" }}
    >
      <div className="flex h-full w-full flex-col">
        <SidebarContent />
      </div>
    </aside>
  );
}
