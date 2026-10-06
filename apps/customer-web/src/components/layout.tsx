import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { ShoppingBag, ShoppingCart, LifeBuoy, Package } from "lucide-react";
import { useAuth } from "@/stores/auth-store";
import { Toaster } from "@/components/toaster";

const link = ({ isActive }: { isActive: boolean }) =>
  isActive ? "ns-navlink is-active" : "ns-navlink";

export function Shell() {
  const user = useAuth((s) => s.user);
  const booted = useAuth((s) => s.booted);
  const logout = useAuth((s) => s.logout);
  const nav = useNavigate();
  return (
    <div className="ns-app">
      <header className="ns-header">
        <div className="ns-shell ns-header-row">
          <Link to="/" className="ns-brand">
            <ShoppingBag size={20} aria-hidden />
            <span>Northstar Shop</span>
          </Link>
          <nav className="ns-nav" aria-label="Primary">
            <NavLink to="/products" className={link}>Products</NavLink>
            <NavLink to="/orders" className={link}>Orders</NavLink>
            <NavLink to="/support" className={link}>Support</NavLink>
          </nav>
          <div className="ns-header-actions">
            <NavLink to="/cart" className="ns-iconbtn" aria-label="Cart">
              <ShoppingCart size={18} aria-hidden />
            </NavLink>
            {!booted ? null : user ? (
              <>
                <span className="ns-muted hidden sm:inline" title={user.email}>{user.name}</span>
                <button
                  className="ns-btn ns-btn-secondary ns-btn-sm"
                  onClick={() => {
                    logout();
                    nav("/");
                  }}
                >
                  Log out
                </button>
              </>
            ) : (
              <>
                <NavLink to="/login" className="ns-btn ns-btn-secondary ns-btn-sm">Log in</NavLink>
                <NavLink to="/signup" className="ns-btn ns-btn-primary ns-btn-sm">Sign up</NavLink>
              </>
            )}
          </div>
        </div>
      </header>
      <main className="ns-shell ns-main">
        <Outlet />
      </main>
      <footer className="ns-footer">
        <div className="ns-shell ns-footer-row">
          <span className="ns-muted">© Northstar Shop · Phase 1 prototype shell</span>
          <span className="ns-muted ns-footer-links">
            <span className="ns-inline"><Package size={14} aria-hidden /> Orders</span>
            <span className="ns-inline"><LifeBuoy size={14} aria-hidden /> Support</span>
          </span>
        </div>
      </footer>
      <Toaster />
    </div>
  );
}
