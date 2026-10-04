import { Suspense } from "react";
import { Link, Outlet } from "react-router-dom";

// Shop layout: customer surface shell with section nav (Phase 7).
export function ShopLayout() {
  return (
    <div className="min-h-screen bg-white text-slate-900">
      <nav className="flex gap-4 border-b p-4 text-sm" aria-label="Shop">
        <Link to="/shop/orders" className="font-semibold">
          Northstar Shop
        </Link>
        <Link to="/shop/orders">Orders</Link>
      </nav>
      <Suspense fallback={<p className="p-8 text-sm">Loading…</p>}>
        <Outlet />
      </Suspense>
    </div>
  );
}
