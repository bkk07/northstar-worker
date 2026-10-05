import { ErrorState, LoadingState } from "@/shared/ui/feedback";
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
  if (items.length === 0) return <p className="text-sm text-slate-500">No memory recorded.</p>;
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left text-slate-500">
          <th>Key</th>
          <th>Source</th>
          <th>Trust</th>
          <th>Fact</th>
        </tr>
      </thead>
      <tbody>
        {items.map((item) => (
          <tr key={item.id} className="border-t align-top">
            <td className="font-mono text-xs">{item.key}</td>
            <td className="text-xs">{item.source_type}</td>
            <td>
              <span
                className={`rounded px-1.5 py-0.5 text-xs font-medium ${item.trust === "trusted" ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"}`}
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
  );
}
