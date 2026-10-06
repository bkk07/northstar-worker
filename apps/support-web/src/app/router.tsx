import { createBrowserRouter, Navigate } from "react-router-dom";
import { ConsoleShell } from "@/components/layout";
import { LoginPage } from "@/pages/auth/LoginPage";
import { DashboardPage } from "@/pages/dashboard/DashboardPage";
import { TicketsPage, TicketDetailPage } from "@/pages/tickets/TicketsPage";

export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  {
    path: "/",
    element: <ConsoleShell />,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: "dashboard", element: <DashboardPage /> },
      { path: "tickets", element: <TicketsPage /> },
      { path: "tickets/:id", element: <TicketDetailPage /> },
      { path: "*", element: <Navigate to="/dashboard" replace /> },
    ],
  },
]);
