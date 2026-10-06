import { Navigate, createBrowserRouter, useLocation } from "react-router-dom";
import type { ReactNode } from "react";
import { ConsoleShell } from "@/components/layout";
import { Spinner } from "@/components/ui";
import { useStaffAuth } from "@/stores/auth-store";
import { LoginPage } from "@/pages/auth/LoginPage";
import { DashboardPage } from "@/pages/dashboard/DashboardPage";
import { TicketsPage, TicketDetailPage } from "@/pages/tickets/TicketsPage";

function StaffOnly({ children }: { children: ReactNode }) {
  const user = useStaffAuth((s) => s.user);
  const booted = useStaffAuth((s) => s.booted);
  const location = useLocation();
  if (!booted) return <Spinner label="Restoring staff session…" />;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  return <>{children}</>;
}

export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  {
    path: "/",
    element: (
      <StaffOnly>
        <ConsoleShell />
      </StaffOnly>
    ),
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      { path: "dashboard", element: <DashboardPage /> },
      { path: "tickets", element: <TicketsPage /> },
      { path: "tickets/:id", element: <TicketDetailPage /> },
      { path: "*", element: <Navigate to="/dashboard" replace /> },
    ],
  },
]);
