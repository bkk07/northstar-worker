import {
  Bot,
  LifeBuoy,
  MessageSquarePlus,
  Package,
  ShoppingBag,
  Trash2,
  type LucideIcon,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { deleteSession, loadSessions, type ChatSession } from "@/features/worker/assistant/chatHistory";
import { cn } from "@/shared/lib/utils";

export type SideLink = {
  to: string;
  label: string;
  desc: string;
  match: string;
  icon: LucideIcon;
};

export const SIDE_LINKS: SideLink[] = [
  { to: "/worker/assistant", label: "Support console", desc: "Chat with the bot", match: "/worker", icon: Bot },
  { to: "/shop/orders", label: "Shop", desc: "Customer orders", match: "/shop", icon: ShoppingBag },
  { to: "/ops/tickets", label: "Tickets", desc: "Support queue", match: "/ops", icon: LifeBuoy },
  { to: "/products", label: "Products", desc: "Catalog & policies", match: "/products", icon: Package },
];

export function isSideActive(pathname: string, match: string) {
  return pathname === match || pathname.startsWith(`${match}/`);
}

/** ChatGPT-style conversation history (local sessions, newest first). */
function ChatHistory({ onNavigate }: { onNavigate?: () => void }) {
  const location = useLocation();
  const navigate = useNavigate();
  const [sessions, setSessions] = useState<ChatSession[]>([]);

  useEffect(() => {
    setSessions(loadSessions());
  }, [location.pathname, location.search]);

  if (sessions.length === 0) return null;
  return (
    <div className="mt-5">
      <p className="px-3 pb-1.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-400">
        Conversations
      </p>
      <ul className="space-y-0.5">
        {sessions.map((session) => {
          const active =
            location.pathname === "/worker/assistant" &&
            new URLSearchParams(location.search).get("sid") === session.id;
          return (
            <li key={session.id} className="group relative">
              <button
                type="button"
                onClick={() => {
                  navigate(`/worker/assistant?sid=${session.id}`);
                  onNavigate?.();
                }}
                title={session.title}
                className={cn("ns-side-link w-full pr-8 text-left", active && "ns-side-link-active")}
              >
                <span className="min-w-0 truncate">{session.title}</span>
              </button>
              <button
                type="button"
                aria-label={`Delete ${session.title}`}
                onClick={() => setSessions(deleteSession(session.id))}
                className="absolute right-1.5 top-1/2 hidden -translate-y-1/2 rounded-md p-1.5 text-slate-400 hover:bg-slate-200 hover:text-slate-700 group-hover:block"
              >
                <Trash2 aria-hidden className="h-3.5 w-3.5" />
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

/** Shared sidebar body: logo, new chat, nav, history, user. Desktop + mobile drawer. */
export function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const location = useLocation();
  const navigate = useNavigate();
  return (
    <div className="flex h-full flex-col border-r border-slate-200 bg-white">
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 pb-4 pt-6">
        <div
          aria-hidden
          className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-600 text-sm font-bold text-white shadow-lg"
        >
          N
        </div>
        <div className="min-w-0">
          <p className="truncate text-[15px] font-semibold tracking-tight text-slate-900">Northstar</p>
          <p className="text-xs text-slate-500">Support</p>
        </div>
        <span className="ml-auto rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] font-medium text-slate-500">
          v0.1
        </span>
      </div>

      {/* New chat */}
      <div className="px-3 pb-3">
        <button
          type="button"
          onClick={() => {
            navigate("/worker/assistant?new=1");
            onNavigate?.();
          }}
          className="ns-btn ns-btn-primary w-full"
        >
          <MessageSquarePlus aria-hidden className="h-4 w-4" />
          New chat
        </button>
      </div>

      {/* Nav */}
      <nav aria-label="Primary" className="min-h-0 flex-1 overflow-y-auto px-3 pb-4">
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
                      active ? "text-indigo-600" : "text-slate-400",
                    )}
                  />
                  <span className="min-w-0">
                    <span className="block truncate leading-5">{link.label}</span>
                    <span
                      className={cn(
                        "block truncate text-xs font-normal",
                        active ? "text-indigo-600" : "text-slate-400",
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
        <ChatHistory onNavigate={onNavigate} />
      </nav>

      {/* User bottom */}
      <div className="border-t border-slate-200 p-3">
        <div className="flex items-center gap-2.5 rounded-xl px-2 py-2">
          <span
            aria-hidden
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-xs font-semibold text-white"
          >
            OP
          </span>
          <span className="min-w-0 flex-1">
            <span className="block truncate text-[13px] font-medium text-slate-900">Operator</span>
            <span className="block truncate text-xs text-slate-500">Duty ops · sandbox</span>
          </span>
          <span
            aria-hidden
            className="h-2 w-2 shrink-0 rounded-full bg-emerald-500"
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
    <aside className="hidden shrink-0 border-r border-slate-200 bg-white lg:sticky lg:top-0 lg:flex lg:h-screen lg:w-[264px]">
      <div className="flex h-full w-full flex-col">
        <SidebarContent />
      </div>
    </aside>
  );
}
