import { createBrowserRouter, Navigate } from "react-router-dom";
import { Shell } from "@/components/layout";
import { HomePage } from "@/pages/home/HomePage";
import { ProductsPage, ProductDetailPage } from "@/pages/products/ProductsPage";
import { CartPage } from "@/pages/cart/CartPage";
import { OrdersPage, OrderDetailPage } from "@/pages/orders/OrdersPage";
import { LoginPage, SignupPage, SupportPage, TicketDetailPage } from "@/pages/auth-support/AuthSupportPages";

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
      { path: "cart", element: <CartPage /> },
      { path: "orders", element: <OrdersPage /> },
      { path: "orders/:id", element: <OrderDetailPage /> },
      { path: "support", element: <SupportPage /> },
      { path: "tickets/:id", element: <TicketDetailPage /> },
      { path: "*", element: <Navigate to="/" replace /> },
    ],
  },
]);
