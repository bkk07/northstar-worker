import { ErrorState, LoadingState } from "@/shared/ui/feedback";
import { getErrorMessage } from "@/shared/lib/errors";
import { useTaskScreenshots, useTaskTimeline } from "../../hooks/useWorker";
import { workerUiActions, useWorkerUiStore } from "../../stores/workerUiStore";
import type { AuditEventRead, ScreenshotRead } from "../../types";

// Decision/graph nodes get the highlight treatment; transitions stay quiet.
const NODE_STYLES: Record<string, string> = {
  contract: "bg-indigo-100 text-indigo-800",
  policy_check: "bg-amber-100 text-amber-800",
  verify: "bg-green-100 text-green-800",
  human_approval: "bg-orange-100 text-orange-800",
  clarification: "bg-orange-100 text-orange-800",
  recover: "bg-red-100 text-red-800",
  classify: "bg-red-100 text-red-800",
};

export function TaskTimeline({ taskId }: { taskId: string }) {
  const timeline = useTaskTimeline(taskId);
  const shots = useTaskScreenshots(taskId);
  const kindFilter = useWorkerUiStore().timelineKindFilter;
  if (timeline.isPending) return <LoadingState what="timeline" />;
  if (timeline.isError)
    return (
      <ErrorState message={getErrorMessage(timeline.error)} onRetry={() => timeline.refetch()} />
    );
  return (
    <TaskTimelineView
      events={timeline.data ?? []}
      screenshots={shots.data ?? []}
      kindFilter={kindFilter}
      onFilter={(kind) => workerUiActions.filterTimeline(kind)}
      liveStatus={timeline.liveStatus}
    />
  );
}

// Split for testability: pure view over events + screenshots.
export function TaskTimelineView({
  events,
  screenshots,
  kindFilter,
  onFilter,
  liveStatus,
}: {
  events: AuditEventRead[];
  screenshots: ScreenshotRead[];
  kindFilter: string;
  onFilter: (kind: string) => void;
  liveStatus: string;
}) {
  const kinds = ["all", ...Array.from(new Set(events.map((event) => event.kind)))];
  const visible =
    kindFilter === "all" ? events : events.filter((event) => event.kind === kindFilter);
  return (
    <div>
      <div className="flex items-center gap-2 text-sm">
        <label htmlFor="timeline-filter">Kind</label>
        <select
          id="timeline-filter"
          value={kindFilter}
          onChange={(event) => onFilter(event.target.value)}
          className="rounded border px-2 py-1"
        >
          {kinds.map((kind) => (
            <option key={kind} value={kind}>
              {kind}
            </option>
          ))}
        </select>
        <span aria-live="polite" className="text-xs text-slate-500">
          live: {liveStatus} · {visible.length} events
        </span>
      </div>
      {visible.length === 0 ? (
        <p className="mt-3 text-sm text-slate-500">No events yet — the run has not started.</p>
      ) : (
        <ol className="mt-3 flex flex-col gap-2">
          {visible.map((event) => (
            <li key={event.id} className="rounded border p-2 text-sm">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-xs text-slate-500">#{event.seq}</span>
                {event.node && (
                  <span
                    className={`rounded px-1.5 py-0.5 text-xs font-medium ${NODE_STYLES[event.node] ?? "bg-slate-100 text-slate-600"}`}
                  >
                    {event.node}
                  </span>
                )}
                <span className="font-medium">{event.kind}</span>
                {event.kind === "failure.classified" && event.error_type && (
                  <span
                    role="status"
                    className="rounded bg-red-100 px-1.5 py-0.5 text-xs font-medium text-red-800"
                  >
                    FAILURE: {event.error_type}
                  </span>
                )}
                {(event.kind === "recovery.decided" || event.kind === "recovery.probe") && (
                  <span
                    role="status"
                    className="rounded bg-amber-100 px-1.5 py-0.5 text-xs font-medium text-amber-800"
                  >
                    RECOVERY: {event.status ?? event.kind}
                  </span>
                )}
                {event.kind === "policy.decision" && event.policy_result && (
                  <span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs">
                    {event.policy_result}
                  </span>
                )}
                {event.kind === "verification.result" && event.verification_result && (
                  <span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs">
                    {event.verification_result}
                  </span>
                )}
              </div>
              <p className="mt-1 text-xs text-slate-500">
                {new Date(event.ts).toLocaleString()}
                {event.tool ? ` · ${event.tool}` : ""}
                {event.retry_count > 0 ? ` · retry ${event.retry_count}` : ""}
              </p>
            </li>
          ))}
        </ol>
      )}
      <section aria-label="Screenshot gallery" className="mt-4">
        <h3 className="text-sm font-medium">Screenshots ({screenshots.length})</h3>
        {screenshots.length === 0 ? (
          <p className="mt-1 text-sm text-slate-500">No screenshots captured.</p>
        ) : (
          <ul className="mt-2 flex flex-col gap-1 text-sm">
            {screenshots.map((shot, index) => (
              <li key={`${shot.run_id}-${shot.label}-${index}`} className="font-mono text-xs">
                {shot.label}: {shot.path}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
