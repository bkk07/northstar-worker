import { lazy } from "react";
import { Navigate, createBrowserRouter } from "react-router-dom";
import { EvaluationLayout, OpsLayout, RootLayout, WorkerLayout } from "@/app/layouts/layouts";
import { ShopLayout } from "@/app/layouts/ShopLayout";

// One React app serves all four surfaces (plan §12). Feature routes are
// lazy-loaded per module; other surfaces keep shells until their phase.
const ShopOrdersPage = lazy(() => import("@/features/shop/pages/ShopOrdersPage"));
const ShopOrderDetailPage = lazy(() => import("@/features/shop/pages/ShopOrderDetailPage"));
const ShopTicketPage = lazy(() => import("@/features/shop/pages/ShopTicketPage"));

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
      { path: "ops/*", element: <OpsLayout /> },
      { path: "worker/*", element: <WorkerLayout /> },
      { path: "evaluation/*", element: <EvaluationLayout /> },
      { path: "*", element: <Navigate to="/shop/orders" replace /> },
    ],
  },
]);
