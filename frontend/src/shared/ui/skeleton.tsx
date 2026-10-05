import { cn } from "@/shared/lib/utils";

/**
 * Skeleton rows for loading panels.
 * role="status" + aria-label preserved for AT; shimmer disabled
 * under prefers-reduced-motion via index.css.
 */
export function Skeleton({
  className,
  lines = 3,
  label = "Loading",
}: {
  className?: string;
  lines?: number;
  label?: string;
}) {
  return (
    <div role="status" aria-label={label} className={cn("space-y-2", className)}>
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className="ns-skeleton h-4"
          style={{ width: i === 0 ? "38%" : i === lines - 1 ? "72%" : "100%" }}
        />
      ))}
      <span className="sr-only">{label}…</span>
    </div>
  );
}

export function SkeletonCard({ className }: { className?: string }) {
  return (
    <div role="status" aria-label="Loading card" className={cn("ns-card ns-card-pad", className)}>
      <div className="ns-skeleton h-4 w-1/3" />
      <div className="mt-3 space-y-2">
        <div className="ns-skeleton h-4 w-full" />
        <div className="ns-skeleton h-4 w-5/6" />
      </div>
    </div>
  );
}
