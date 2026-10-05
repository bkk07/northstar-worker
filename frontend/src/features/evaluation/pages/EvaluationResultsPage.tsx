import { LatestResults } from "../results/components/RunResults";
import { PageHeader } from "@/shared/ui/page-header";

export default function EvaluationResultsPage() {
  return (
    <main className="ns-page space-y-5">
      <PageHeader
        eyebrow="Evaluation"
        title="Latest suite run"
        desc="§26 metrics table with per-scenario drilldown. Same data as eval/reports/*.json — safety violations must read zero."
      />
      <LatestResults />
    </main>
  );
}
