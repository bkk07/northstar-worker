import { NavLink, Outlet, Link } from "react-router-dom";
import { LayoutDashboard, Inbox, Headset } from "lucide-react";

const link = ({ isActive }: { isActive: boolean }) =>
  isActive ? "sp-side-link is-active" : "sp-side-link";

export function ConsoleShell() {
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
        </nav>
        <div className="sp-side-foot">
          <span className="sp-muted">Phase 1 shell · AI in Phase 8+</span>
        </div>
      </aside>
      <div className="sp-main-col">
        <header className="sp-topbar">
          <span className="sp-muted">Internal console</span>
          <span className="sp-badge sp-badge-info">admin@shop.local</span>
        </header>
        <main className="sp-main">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
