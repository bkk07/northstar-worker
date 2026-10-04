import { createBrowserRouter } from "react-router-dom";
import {
  EvaluationLayout,
  OpsLayout,
  RootLayout,
  ShopLayout,
  WorkerLayout,
} from "@/app/layouts/layouts";

// One React app serves all four surfaces (plan §12). Each route is
// lazy-loaded per-feature in later phases; Phase 1 keeps shells.
export const routePaths = ["/shop", "/ops", "/worker", "/evaluation"] as const;

export const router = createBrowserRouter([
  {
    path: "/",
    element: <RootLayout />,
    children: [
      { path: "shop/*", element: <ShopLayout /> },
      { path: "ops/*", element: <OpsLayout /> },
      { path: "worker/*", element: <WorkerLayout /> },
      { path: "evaluation/*", element: <EvaluationLayout /> },
      { path: "*", element: <ShopLayout /> },
    ],
  },
]);
