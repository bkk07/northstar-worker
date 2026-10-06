import { Navigate, createBrowserRouter, useLocation } from "react-router-dom";
import type { ReactNode } from "react";
import { Shell } from "@/components/layout";
import { Spinner } from "@/components/ui";
import { useAuth } from "@/stores/auth-store";
import { HomePage } from "@/pages/home/HomePage";
import { CartPage, ProductDetailPage, ProductsPage } from "@/pages/shop/ShopPages";
import { CheckoutPage, OrderDetailPage, OrdersPage } from "@/pages/orders/OrdersPage";
import { LoginPage, SignupPage, SupportPage, TicketDetailPage } from "@/pages/auth-support/AuthSupportPages";

function Protected({ children }: { children: ReactNode }) {
  const user = useAuth((s) => s.user);
  const booted = useAuth((s) => s.booted);
  const location = useLocation();
  if (!booted) return <Spinner label="Restoring session…" />;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  return <>{children}</>;
}

export const router = createBrowserRouter([
  {
    path: "/",
    element: <Shell />,
    children: [
      { index: true, element: <HomePage /> },
      { path: "login", element: <LoginPage /> },
      { path: "signup", element: <SignupPage /> },
      { path: "products", element: <ProductsPage /> },
      { path: "products/:id", element: <ProductDetailPage /> },
      { path: "cart", element: <Protected><CartPage /></Protected> },
      { path: "checkout", element: <Protected><CheckoutPage /></Protected> },
      { path: "orders", element: <Protected><OrdersPage /></Protected> },
      { path: "orders/:id", element: <Protected><OrderDetailPage /></Protected> },
      { path: "support", element: <Protected><SupportPage /></Protected> },
      { path: "tickets/:id", element: <Protected><TicketDetailPage /></Protected> },
      { path: "*", element: <Navigate to="/" replace /> },
    ],
  },
]);
