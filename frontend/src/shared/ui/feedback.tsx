import { TriangleAlert } from "lucide-react";
import { EmptyState as NewEmptyState } from "@/shared/ui/empty-state";
import { Skeleton } from "@/shared/ui/skeleton";

/** Compat: LoadingState keeps role="status" for AT + tests. */
export function LoadingState({ what }: { what: string }) {
  return (
    <div className="space-y-2">
      <Skeleton label={`Loading ${what}`} lines={2} />
      <p className="text-xs text-slate-500">Loading {what}…</p>
    </div>
  );
}

/** Compat: ErrorState keeps role="alert" for AT + tests. */
export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div
      role="alert"
      className="rounded-2xl border border-red-200 bg-red-50/60 p-4 text-sm text-red-900"
    >
      <p className="flex items-center gap-2 font-semibold">
        <TriangleAlert aria-hidden className="h-4 w-4" />
        Something went wrong
      </p>
      <p className="mt-1 text-red-800/90">{message}</p>
      {onRetry && (
        <button type="button" onClick={onRetry} className="ns-btn ns-btn-secondary ns-btn-sm mt-3">
          Retry
        </button>
      )}
    </div>
  );
}

/** Compat re-export: single EmptyState implementation lives in empty-state.tsx. */
export function EmptyState({
  title,
  desc,
  action,
}: {
  title: string;
  desc?: string;
  action?: React.ReactNode;
}) {
  return <NewEmptyState title={title} desc={desc} action={action} />;
}
