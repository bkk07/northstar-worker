import { motion, useReducedMotion } from "framer-motion";
import { CheckCircle2, Circle, Loader2 } from "lucide-react";
import type { TicketRead } from "../types";
import { cn } from "@/shared/lib/utils";

const RESOLUTION: Record<string, string> = {
  open: "We have received your ticket and will look into it.",
  in_progress: "Our team is working on your ticket.",
  waiting_on_customer: "We need more information from you.",
  resolved: "Your ticket has been resolved.",
  closed: "This ticket is closed.",
};

const STEPS = [
  { key: "received", label: "Received", desc: "Ticket raised" },
  { key: "progress", label: "In progress", desc: "Team is on it" },
  { key: "resolved", label: "Resolved", desc: "Fix confirmed" },
  { key: "closed", label: "Closed", desc: "Wrapped up" },
] as const;

function stepIndex(status: string): number {
  switch (status) {
    case "open":
      return 0;
    case "in_progress":
    case "waiting_on_customer":
      return 1;
    case "resolved":
      return 2;
    case "closed":
      return 3;
    default:
      return 0;
  }
}

/** Amazon-style tracking timeline for a customer ticket. */
export function TicketStatusCard({ ticket }: { ticket: TicketRead }) {
  const reduce = useReducedMotion();
  const current = stepIndex(ticket.status);
  const needsAttention = ticket.status === "waiting_on_customer";

  return (
    <article aria-label={`Ticket ${ticket.code}`} className="ns-card overflow-hidden">
      <div className="ns-card-pad border-b border-slate-100">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-[15px] font-semibold tracking-tight">{ticket.code}</h2>
            <p className="mt-0.5 text-[13px] text-slate-600">{ticket.subject}</p>
          </div>
          <span className="ns-badge border-slate-200 bg-slate-100 text-slate-600">
            {ticket.category}
          </span>
        </div>
        <p className="mt-1 font-mono text-xs text-slate-400">Status: {ticket.status}</p>
      </div>

      {/* Tracking timeline */}
      <ol className="ns-card-pad space-y-0">
        {STEPS.map((step, i) => {
          const done = i < current;
          const active = i === current;
          return (
            <motion.li
              key={step.key}
              initial={reduce ? false : { opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: reduce ? 0 : i * 0.08, duration: 0.3 }}
              className="relative flex gap-3 pb-5 last:pb-0"
            >
              {/* Rail */}
              {i < STEPS.length - 1 && (
                <span
                  aria-hidden
                  className={cn(
                    "absolute left-[11px] top-6 h-[calc(100%-1.25rem)] w-0.5 rounded",
                    i < current ? "bg-emerald-500" : "bg-slate-200",
                  )}
                />
              )}
              <span aria-hidden className="relative z-10 shrink-0">
                {done ? (
                  <CheckCircle2 className="h-6 w-6 text-emerald-500" fill="white" />
                ) : active ? (
                  <span className="relative flex h-6 w-6">
                    {!reduce && (
                      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-indigo-400 opacity-40" />
                    )}
                    <Loader2 className="h-6 w-6 text-indigo-600" fill="white" />
                  </span>
                ) : (
                  <Circle className="h-6 w-6 text-slate-300" fill="white" />
                )}
              </span>
              <div className="min-w-0 pt-0.5">
                <p
                  className={cn(
                    "text-sm font-semibold",
                    done || active ? "text-slate-900" : "text-slate-400",
                  )}
                >
                  {step.label}
                  {active && (
                    <span className="ml-2 rounded-full bg-indigo-50 px-2 py-0.5 text-[11px] font-medium text-indigo-700">
                      current
                    </span>
                  )}
                </p>
                <p className="text-xs text-slate-500">{step.desc}</p>
              </div>
            </motion.li>
          );
        })}
      </ol>

      <div
        className={cn(
          "border-t px-4 py-3 text-[13px] leading-5 sm:px-5",
          needsAttention
            ? "border-amber-200 bg-amber-50/70 text-amber-900"
            : "border-slate-100 bg-slate-50/70 text-slate-600",
        )}
      >
        {needsAttention && (
          <p className="mb-1 text-xs font-semibold uppercase tracking-wider">
            Action needed
          </p>
        )}
        {RESOLUTION[ticket.status] ?? ticket.status}
      </div>
    </article>
  );
}
