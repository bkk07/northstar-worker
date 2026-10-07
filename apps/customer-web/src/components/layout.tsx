import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { Menu, ShoppingBag, ShoppingCart, LifeBuoy, Package, X } from "lucide-react";
import { useAuth } from "@/stores/auth-store";
import { useCart } from "@/stores/cart-store";
import { Toaster } from "@/components/toaster";

const link = ({ isActive }: { isActive: boolean }) =>
  isActive ? "ns-navlink is-active" : "ns-navlink";

export function Shell() {
  const user = useAuth((s) => s.user);
  const booted = useAuth((s) => s.booted);
  const logout = useAuth((s) => s.logout);
  const cart = useCart((s) => s.cart);
  const refreshCart = useCart((s) => s.refresh);
  const [menuOpen, setMenuOpen] = useState(false);
  const nav = useNavigate();

  useEffect(() => {
    if (booted && user) void refreshCart();
  }, [booted, user, refreshCart]);

  const count = cart?.item_count ?? 0;
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
            <NavLink to="/cart" className="ns-iconbtn relative" aria-label={`Cart${count ? `, ${count} items` : ""}`}>
              <ShoppingCart size={18} aria-hidden />
              {count > 0 ? (
                <span
                  className="absolute -right-1.5 -top-1.5 flex h-5 min-w-5 items-center justify-center rounded-full bg-indigo-600 px-1 text-[11px] font-bold text-white"
                  aria-hidden
                >
                  {count > 99 ? "99+" : count}
                </span>
              ) : null}
            </NavLink>
            <button
              className="ns-iconbtn sm:hidden"
              aria-label={menuOpen ? "Close menu" : "Open menu"}
              aria-expanded={menuOpen}
              onClick={() => setMenuOpen((v) => !v)}
            >
              {menuOpen ? <X size={18} aria-hidden /> : <Menu size={18} aria-hidden />}
            </button>
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
        {menuOpen ? (
          <nav className="border-t px-4 py-2 sm:hidden" aria-label="Mobile">
            {[
              ["/products", "Products"],
              ["/orders", "Orders"],
              ["/support", "Support"],
              ["/cart", `Cart${count ? ` (${count})` : ""}`],
            ].map(([to, label]) => (
              <NavLink
                key={to}
                to={to}
                className={link}
                onClick={() => setMenuOpen(false)}
              >
                <span className="block py-1">{label}</span>
              </NavLink>
            ))}
          </nav>
        ) : null}
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
