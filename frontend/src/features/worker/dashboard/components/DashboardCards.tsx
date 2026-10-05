import { animate, motion, useReducedMotion } from "framer-motion";
import { useEffect, useRef } from "react";
import { Activity, CheckCircle2, Database, HelpCircle, Inbox, Server } from "lucide-react";
import { ErrorState, LoadingState } from "@/shared/ui/feedback";
import { getErrorMessage } from "@/shared/lib/errors";
import { Card, CardBody } from "@/shared/ui/card";
import {
  useApprovals,
  useClarifications,
  useEnvironmentStatus,
  useWorkerTasks,
} from "../../hooks/useWorker";
import type { EnvironmentStatus } from "../../types";
import { cn } from "@/shared/lib/utils";

export function DashboardCards() {
  const status = useEnvironmentStatus();
  const tasks = useWorkerTasks();
  if (status.isPending || tasks.isPending) return <LoadingState what="dashboard" />;
  if (status.isError)
    return <ErrorState message={getErrorMessage(status.error)} onRetry={() => status.refetch()} />;
  if (!status.data) return <LoadingState what="dashboard" />;
  return <DashboardCardsView status={status.data} taskCount={(tasks.data ?? []).length} />;
}

/** Animated integer counter (instant under reduced motion). */
function CountUp({ value }: { value: number }) {
  const reduce = useReducedMotion();
  const ref = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    if (reduce) {
      node.textContent = String(value);
      return;
    }
    const controls = animate(0, value, {
      duration: 0.6,
      ease: "easeOut",
      onUpdate: (v) => {
        node.textContent = String(Math.round(v));
      },
    });
    return () => controls.stop();
  }, [value, reduce]);
  return <span ref={ref}>{value}</span>;
}

function HealthDot({ ok }: { ok: boolean }) {
  return (
    <span className="relative flex h-2 w-2" aria-hidden>
      {!ok ? (
        <span className="h-2 w-2 rounded-full bg-red-500" />
      ) : (
        <>
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60 motion-reduce:animate-none" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
        </>
      )}
    </span>
  );
}

// Split for testability: pure view over status + counts.
export function DashboardCardsView({
  status,
  taskCount,
}: {
  status: EnvironmentStatus;
  taskCount: number;
}) {
  const backendOk = status.backend === "ok" || status.backend === "healthy";
  const dbOk = status.database === "ok" || status.database === "healthy";
  const cards = [
    { label: "Backend", icon: Server, display: status.backend, ok: backendOk, count: null as number | null, hint: "API reachability" },
    { label: "Database", icon: Database, display: status.database, ok: dbOk, count: null, hint: "Postgres source of truth" },
    { label: "Tasks", icon: Activity, display: null, ok: true, count: taskCount, hint: "Latest 50 runs" },
    { label: "Pending tasks", icon: Inbox, display: null, ok: status.pending_tasks === 0, count: status.pending_tasks, hint: "Awaiting a runner" },
    { label: "Approvals waiting", icon: CheckCircle2, display: null, ok: status.pending_approvals === 0, count: status.pending_approvals, hint: "Needs operator decision" },
    { label: "Questions waiting", icon: HelpCircle, display: null, ok: status.pending_clarifications === 0, count: status.pending_clarifications, hint: "Needs clarification" },
  ];
  return (
    <dl className="grid grid-cols-2 gap-3 lg:grid-cols-3">
      {cards.map((card) => (
        <motion.div
          key={card.label}
          initial={false}
          whileHover={{ y: -2 }}
          transition={{ type: "tween", duration: 0.18, ease: "easeOut" }}
        >
          <Card lift={false}>
            <CardBody>
              <div className="flex items-center gap-2">
                <card.icon aria-hidden className="h-3.5 w-3.5 text-slate-400" />
                <dt className="text-xs font-medium uppercase tracking-wider text-slate-500">
                  {card.label}
                </dt>
                <span className="ml-auto">
                  <HealthDot ok={card.ok} />
                </span>
              </div>
              <dd className="mt-1.5 truncate text-2xl font-semibold tabular-nums tracking-tight text-slate-900">
                {card.count !== null ? <CountUp value={card.count} /> : card.display}
              </dd>
              <p className="mt-0.5 truncate text-xs text-slate-500">{card.hint}</p>
            </CardBody>
          </Card>
        </motion.div>
      ))}
    </dl>
  );
}

/** Queue donut: approvals vs clarifications vs flowing tasks. */
export function QueueDonut({
  approvals,
  clarifications,
  tasks,
}: {
  approvals: number;
  clarifications: number;
  tasks: number;
}) {
  const reduce = useReducedMotion();
  const total = Math.max(1, approvals + clarifications + tasks);
  const segs = [
    { value: approvals, color: "#f59e0b", label: "Approvals" },
    { value: clarifications, color: "#6366f1", label: "Questions" },
    { value: tasks, color: "#e2e8f0", label: "Tasks" },
  ];
  const R = 34;
  const C = 2 * Math.PI * R;
  let offset = 0;
  return (
    <div className="flex items-center gap-4">
      <svg viewBox="0 0 84 84" className="h-20 w-20 shrink-0" role="img" aria-label={`Queue: ${approvals} approvals, ${clarifications} questions, ${tasks} tasks`}>
        <circle cx="42" cy="42" r={R} fill="none" stroke="#f1f5f9" strokeWidth="10" />
        {segs.map((s) => {
          const frac = s.value / total;
          const el = (
            <motion.circle
              key={s.label}
              cx="42"
              cy="42"
              r={R}
              fill="none"
              stroke={s.color}
              strokeWidth="10"
              strokeLinecap="round"
              strokeDasharray={`${Math.max(0, frac * C - 3)} ${C}`}
              strokeDashoffset={-offset}
              transform="rotate(-90 42 42)"
              initial={reduce ? false : { opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.5 }}
            />
          );
          offset += frac * C;
          return el;
        })}
      </svg>
      <ul className="space-y-1.5 text-[13px]">
        {segs.map((s) => (
          <li key={s.label} className="flex items-center gap-2">
            <span aria-hidden className="h-2 w-2 rounded-full" style={{ background: s.color }} />
            <span className="text-slate-500">{s.label}</span>
            <span className="ml-auto pl-4 font-semibold tabular-nums">
              <CountUp value={s.value} />
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function QueueSummary() {
  const approvals = useApprovals();
  const clarifications = useClarifications();
  if (approvals.isPending || clarifications.isPending) return <LoadingState what="queues" />;
  const waiting = (approvals.data ?? []).length + (clarifications.data ?? []).length;
  if (waiting === 0)
    return <p className="text-sm text-slate-500">All clear — nothing waiting for an operator.</p>;
  return (
    <div
      className={cn(
        "inline-flex items-center gap-2 rounded-full border border-amber-200 bg-amber-50 px-3 py-1",
        "text-[13px] font-medium text-amber-900",
      )}
    >
      <span aria-hidden className="relative flex h-1.5 w-1.5">
        <span className="absolute h-full w-full animate-ping rounded-full bg-amber-400 opacity-75 motion-reduce:animate-none" />
        <span className="relative h-1.5 w-1.5 rounded-full bg-amber-500" />
      </span>
      {waiting} item{waiting === 1 ? "" : "s"} waiting for an operator
    </div>
  );
}
