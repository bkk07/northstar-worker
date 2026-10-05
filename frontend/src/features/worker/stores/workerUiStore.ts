import { useSyncExternalStore } from "react";

// UI-only store (no zustand dependency): the selected task plus timeline
// filters. Server state stays in TanStack Query; this holds UI state only.
type WorkerUiState = {
  selectedTaskId: string | null;
  timelineKindFilter: string;
};

let state: WorkerUiState = { selectedTaskId: null, timelineKindFilter: "all" };
const listeners = new Set<() => void>();

function setState(patch: Partial<WorkerUiState>) {
  state = { ...state, ...patch };
  listeners.forEach((notify) => notify());
}

function subscribe(notify: () => void) {
  listeners.add(notify);
  return () => {
    listeners.delete(notify);
  };
}

export function useWorkerUiStore(): WorkerUiState {
  return useSyncExternalStore(subscribe, () => state);
}

export const workerUiActions = {
  selectTask(taskId: string | null) {
    setState({ selectedTaskId: taskId });
  },
  filterTimeline(kind: string) {
    setState({ timelineKindFilter: kind });
  },
};
