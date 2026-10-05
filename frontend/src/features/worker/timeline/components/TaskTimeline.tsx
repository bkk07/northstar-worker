import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ErrorState, LoadingState } from "@/shared/ui/feedback";
import { EmptyState } from "@/shared/ui/empty-state";
import { getErrorMessage } from "@/shared/lib/errors";
import { Badge } from "@/shared/ui/badge";
import { useTaskScreenshots, useTaskTimeline } from "../../hooks/useWorker";
import { workerUiActions, useWorkerUiStore } from "../../stores/workerUiStore";
import type { AuditEventRead, ScreenshotRead } from "../../types";

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
// Live feed animates in via AnimatePresence (reduced-motion safe).
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
  const reduce = useReducedMotion();
  const kinds = ["all", ...Array.from(new Set(events.map((event) => event.kind)))];
  const visible =
    kindFilter === "all" ? events : events.filter((event) => event.kind === kindFilter);
  return (
    <div>
      <div className="flex flex-wrap items-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm">
        <label htmlFor="timeline-filter" className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          Filter
        </label>
        <select
          id="timeline-filter"
          value={kindFilter}
          onChange={(event) => onFilter(event.target.value)}
          className="ns-select py-1 text-[13px]"
        >
          {kinds.map((kind) => (
            <option key={kind} value={kind}>
              {kind}
            </option>
          ))}
        </select>
        <span aria-live="polite" className="ml-auto inline-flex items-center gap-1.5 text-xs text-slate-500">
          <span aria-hidden className="relative flex h-1.5 w-1.5">
            <span className="absolute h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75 motion-reduce:animate-none" />
            <span className="relative h-1.5 w-1.5 rounded-full bg-emerald-500" />
          </span>
          {liveStatus} · {visible.length} events
        </span>
      </div>
      {visible.length === 0 ? (
        <div className="mt-3">
          <EmptyState
            title="No events yet"
            desc="The run has not started. Submit the task and events stream here live."
          />
        </div>
      ) : (
        <ol className="relative mt-4 space-y-0 border-l-2 border-slate-200 pl-0">
          <AnimatePresence initial={false}>
            {visible.map((event) => (
              <motion.li
                key={event.id}
                layout={reduce ? undefined : "position"}
                initial={reduce ? false : { opacity: 0, y: -10, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={reduce ? undefined : { opacity: 0, scale: 0.97 }}
                transition={{ type: "spring", stiffness: 400, damping: 32 }}
                className="relative pb-3 pl-5 last:pb-0"
              >
                <span
                  aria-hidden
                  className="absolute -left-[5px] top-3.5 h-2 w-2 rounded-full border-2 border-white bg-slate-300 shadow"
                />
                <div className="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm shadow-sm">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span className="font-mono text-[11px] text-slate-400">#{event.seq}</span>
                    {event.node && <Badge tone={event.node}>{event.node}</Badge>}
                    <span className="text-[13px] font-semibold">{event.kind}</span>
                    {event.kind === "failure.classified" && event.error_type && (
                      <span role="status" className="ns-badge border-red-200 bg-red-50 text-red-800">
                        FAILURE: {event.error_type}
                      </span>
                    )}
                    {(event.kind === "recovery.decided" || event.kind === "recovery.probe") && (
                      <span role="status" className="ns-badge border-amber-200 bg-amber-50 text-amber-800">
                        RECOVERY: {event.status ?? event.kind}
                      </span>
                    )}
                    {event.kind === "policy.decision" && event.policy_result && (
                      <Badge tone={event.policy_result}>{event.policy_result}</Badge>
                    )}
                    {event.kind === "verification.result" && event.verification_result && (
                      <Badge tone={event.verification_result}>{event.verification_result}</Badge>
                    )}
                  </div>
                  <p className="mt-1 text-xs text-slate-500">
                    {new Date(event.ts).toLocaleString()}
                    {event.tool ? ` · ${event.tool}` : ""}
                    {event.retry_count > 0 ? ` · retry ${event.retry_count}` : ""}
                  </p>
                </div>
              </motion.li>
            ))}
          </AnimatePresence>
        </ol>
      )}
      <section aria-label="Screenshot gallery" className="mt-5 border-t border-slate-100 pt-4">
        <h3 className="text-[13px] font-semibold uppercase tracking-wider text-slate-500">
          Screenshots ({screenshots.length})
        </h3>
        {screenshots.length === 0 ? (
          <p className="mt-1.5 text-[13px] text-slate-500">No screenshots captured yet.</p>
        ) : (
          <ul className="mt-2 space-y-1.5">
            {screenshots.map((shot, index) => (
              <li
                key={`${shot.run_id}-${shot.label}-${index}`}
                className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 font-mono text-xs"
              >
                {shot.label}: {shot.path}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
