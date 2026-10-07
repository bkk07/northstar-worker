import { NavLink, Outlet, Link, useNavigate } from "react-router-dom";
import { LayoutDashboard, Inbox, MessageSquareText, Headset } from "lucide-react";
import { useStaffAuth } from "@/stores/auth-store";

const link = ({ isActive }: { isActive: boolean }) =>
  isActive ? "sp-side-link is-active" : "sp-side-link";

export function ConsoleShell() {
  const user = useStaffAuth((s) => s.user);
  const logout = useStaffAuth((s) => s.logout);
  const nav = useNavigate();

  return (
    <div className="sp-app">
      <aside className="sp-sidebar" aria-label="Support navigation">
        <Link to="/dashboard" className="sp-brand">
          <Headset size={20} aria-hidden />
          <span>Support Console</span>
        </Link>
        <nav className="sp-side-nav">
          <NavLink to="/dashboard" className={link}>
            <LayoutDashboard size={16} aria-hidden /> Dashboard
          </NavLink>
          <NavLink to="/tickets" className={link}>
            <Inbox size={16} aria-hidden /> Tickets
          </NavLink>
          <NavLink to="/chat" className={link}>
            <MessageSquareText size={16} aria-hidden /> AI Chat
          </NavLink>
        </nav>
        <div className="sp-side-foot">
          <span className="sp-muted">Phase 2 auth · AI in Phase 8+</span>
        </div>
      </aside>
      <div className="sp-main-col">
        <header className="sp-topbar">
          <span className="sp-muted">Internal console</span>
          <span className="flex items-center gap-2">
            <span className="sp-badge sp-badge-info">{user?.email ?? "staff"}</span>
            <button
              className="sp-btn sp-btn-secondary"
              style={{ padding: "0.25rem 0.625rem", fontSize: 12 }}
              onClick={() => {
                logout();
                nav("/login");
              }}
            >
              Log out
            </button>
          </span>
        </header>
        <main className="sp-main">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
