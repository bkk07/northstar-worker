import { lazy } from "react";
import { Navigate, createBrowserRouter } from "react-router-dom";
import { EvaluationLayout, RootLayout, WorkerLayout } from "@/app/layouts/layouts";
import { OpsAuthLayout, OpsLayout } from "@/app/layouts/OpsLayout";
import { ShopLayout } from "@/app/layouts/ShopLayout";

// One React app serves all four surfaces (plan §12). Feature routes are
// lazy-loaded per module; worker/evaluation keep shells until their phase.
const ShopOrdersPage = lazy(() => import("@/features/shop/pages/ShopOrdersPage"));
const ShopOrderDetailPage = lazy(() => import("@/features/shop/pages/ShopOrderDetailPage"));
const ShopTicketPage = lazy(() => import("@/features/shop/pages/ShopTicketPage"));

const LoginPage = lazy(() => import("@/features/ops/auth/pages/LoginPage"));
const TicketQueuePage = lazy(() => import("@/features/ops/tickets/pages/TicketQueuePage"));
const TicketDetailPage = lazy(() => import("@/features/ops/tickets/pages/TicketDetailPage"));
const CustomerSearchPage = lazy(() => import("@/features/ops/customers/pages/CustomerSearchPage"));
const OrderLookupPage = lazy(() => import("@/features/ops/orders/pages/OrderLookupPage"));

export const routePaths = ["/shop", "/ops", "/worker", "/evaluation"] as const;

export const router = createBrowserRouter([
  {
    path: "/",
    element: <RootLayout />,
    children: [
      {
        path: "shop",
        element: <ShopLayout />,
        children: [
          { index: true, element: <Navigate to="orders" replace /> },
          { path: "orders", element: <ShopOrdersPage /> },
          { path: "orders/:orderCode", element: <ShopOrderDetailPage /> },
          { path: "tickets/:ticketCode", element: <ShopTicketPage /> },
        ],
      },
      {
        path: "ops/login",
        element: <OpsAuthLayout />,
        children: [{ index: true, element: <LoginPage /> }],
      },
      {
        path: "ops",
        element: <OpsLayout />,
        children: [
          { index: true, element: <Navigate to="tickets" replace /> },
          { path: "tickets", element: <TicketQueuePage /> },
          { path: "tickets/:ticketCode", element: <TicketDetailPage /> },
          { path: "customers", element: <CustomerSearchPage /> },
          { path: "orders", element: <OrderLookupPage /> },
          { path: "orders/:orderCode", element: <OrderLookupPage /> },
        ],
      },
      { path: "worker/*", element: <WorkerLayout /> },
      { path: "evaluation/*", element: <EvaluationLayout /> },
      { path: "*", element: <Navigate to="/shop/orders" replace /> },
    ],
  },
]);
