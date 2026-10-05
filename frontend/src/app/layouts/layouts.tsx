import { AppShell } from "@/shared/ui/app-shell";

/** Root shell: single AppShell for every surface (router imports this name). */
export function RootLayout() {
  return <AppShell />;
}

export { WorkerLayout } from "@/features/worker/components/WorkerLayout";
export { EvaluationLayout } from "@/features/evaluation/components/EvaluationLayout";
