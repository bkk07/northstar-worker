import { Outlet } from "react-router-dom";

export function RootLayout() {
  return (
    <div className="min-h-screen bg-white text-slate-900">
      <nav className="flex gap-4 border-b p-4 text-sm">
        <a href="/shop">Shop</a>
        <a href="/ops">Ops</a>
        <a href="/worker">Worker</a>
        <a href="/evaluation">Evaluation</a>
      </nav>
      <Outlet />
    </div>
  );
}

export { WorkerLayout } from "@/features/worker/components/WorkerLayout";
export { EvaluationLayout } from "@/features/evaluation/components/EvaluationLayout";
