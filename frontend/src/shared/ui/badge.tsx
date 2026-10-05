import { cn } from "@/shared/lib/utils";

// Single source of truth for status colours: indigo primary,
// emerald / amber / red for status (spec), slate neutrals.
const TONES: Record<string, string> = {
  // task lifecycle
  pending: "bg-slate-100 text-slate-700 border-slate-200",
  running: "bg-indigo-50 text-indigo-700 border-indigo-200",
  waiting_for_approval: "bg-amber-50 text-amber-800 border-amber-200",
  waiting_for_clarification: "bg-amber-50 text-amber-800 border-amber-200",
  waiting_on_customer: "bg-amber-50 text-amber-800 border-amber-200",
  succeeded: "bg-emerald-50 text-emerald-800 border-emerald-200",
  verified: "bg-emerald-50 text-emerald-800 border-emerald-200",
  failed: "bg-red-50 text-red-800 border-red-200",
  blocked: "bg-red-50 text-red-800 border-red-200",
  inconclusive: "bg-purple-50 text-purple-800 border-purple-200",
  // tickets
  open: "bg-indigo-50 text-indigo-700 border-indigo-200",
  in_progress: "bg-indigo-50 text-indigo-800 border-indigo-200",
  resolved: "bg-emerald-50 text-emerald-800 border-emerald-200",
  closed: "bg-slate-100 text-slate-600 border-slate-200",
  // generic policy
  allow: "bg-emerald-50 text-emerald-800 border-emerald-200",
  human_approval: "bg-amber-50 text-amber-800 border-amber-200",
  block: "bg-red-50 text-red-800 border-red-200",
};

export function Badge({
  tone,
  className,
  children,
  ...rest
}: {
  tone?: string;
  className?: string;
  children: React.ReactNode;
} & React.HTMLAttributes<HTMLSpanElement>) {
  const cls = (tone && TONES[tone]) || "bg-slate-100 text-slate-600 border-slate-200";
  return (
    <span className={cn("ns-badge", cls, className)} {...rest}>
      {children}
    </span>
  );
}

export function StatusDot({ tone }: { tone?: string }) {
  const dot: Record<string, string> = {
    succeeded: "bg-emerald-500",
    verified: "bg-emerald-500",
    running: "bg-indigo-500",
    failed: "bg-red-500",
    blocked: "bg-red-500",
  };
  return (
    <span
      aria-hidden
      className={cn("inline-block h-1.5 w-1.5 rounded-full", (tone && dot[tone]) || "bg-slate-300")}
    />
  );
}
