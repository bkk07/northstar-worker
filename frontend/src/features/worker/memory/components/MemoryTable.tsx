import { Brain } from "lucide-react";
import { ErrorState, LoadingState } from "@/shared/ui/feedback";
import { EmptyState } from "@/shared/ui/empty-state";
import { getErrorMessage } from "@/shared/lib/errors";
import { useTaskMemory } from "../../hooks/useWorker";
import type { MemoryItemRead } from "../../types";

export function MemoryTable({ taskId }: { taskId: string }) {
  const memory = useTaskMemory(taskId);
  if (memory.isPending) return <LoadingState what="memory" />;
  if (memory.isError)
    return <ErrorState message={getErrorMessage(memory.error)} onRetry={() => memory.refetch()} />;
  return <MemoryTableView items={memory.data ?? []} />;
}

// Split for testability: pure view over memory rows.
export function MemoryTableView({ items }: { items: MemoryItemRead[] }) {
  if (items.length === 0)
    return (
      <EmptyState
        title="No memory recorded."
        desc="Facts with provenance appear here once the run observes the world."
        icon={Brain}
      />
    );
  return (
    <div className="ns-table-wrap">
      <table className="ns-table">
        <thead>
          <tr>
            <th scope="col">Key</th>
            <th scope="col">Source</th>
            <th scope="col">Trust</th>
            <th scope="col">Fact</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id}>
              <td className="font-mono text-xs">{item.key}</td>
              <td className="text-xs">{item.source_type}</td>
              <td>
                <span
                  className={`ns-badge ${item.trust === "trusted" ? "border-emerald-200 bg-emerald-50 text-emerald-800" : "border-red-200 bg-red-50 text-red-800"}`}
                >
                  {item.trust}
                </span>
              </td>
              <td className="max-w-md truncate font-mono text-xs" title={JSON.stringify(item.value)}>
                {JSON.stringify(item.value).slice(0, 120)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
