import { useState } from "react";
import { ErrorState, LoadingState } from "@/shared/ui/feedback";
import { getErrorMessage } from "@/shared/lib/errors";
import {
  useArmFault,
  useEnvironmentStatus,
  useResetWorld,
  useSeedWorld,
} from "../../hooks/useWorker";

const FAULT_TYPES = [
  "HTTP_500_BEFORE_COMMIT",
  "HTTP_500_AFTER_COMMIT",
  "TIMEOUT",
  "VALIDATION_ERROR",
  "DUPLICATE_EFFECT",
  "SESSION_EXPIRY",
];

const FAULT_TARGETS = [
  "ops.replacements",
  "ops.refunds",
  "ops.notes",
  "ops.reply",
  "ops.status",
  "ops.customer_search",
];

export function EnvironmentPanel() {
  const status = useEnvironmentStatus();
  if (status.isPending) return <LoadingState what="environment" />;
  if (status.isError) {
    const http = (status.error as { response?: { status?: number } })?.response?.status;
    if (http === 401)
      return (
        <p className="text-sm text-slate-500">
          Log in through Ops first — the environment panel needs an ops session.
        </p>
      );
    return <ErrorState message={getErrorMessage(status.error)} onRetry={() => status.refetch()} />;
  }
  if (!status.data) return <LoadingState what="environment" />;
  const data = status.data;
  return (
    <div className="flex flex-col gap-4 text-sm">
      <ul className="flex gap-4">
        <li>
          backend: <strong>{data.backend}</strong>
        </li>
        <li>
          database: <strong>{data.database}</strong>
        </li>
        <li>
          pending tasks: <strong>{data.pending_tasks}</strong>
        </li>
        <li>
          approvals: <strong>{data.pending_approvals}</strong>
        </li>
        <li>
          clarifications: <strong>{data.pending_clarifications}</strong>
        </li>
      </ul>
      <ArmFaultForm />
      <WorldControls />
    </div>
  );
}

export function ArmFaultForm() {
  const armed = useArmFault();
  const [faultType, setFaultType] = useState(FAULT_TYPES[2]);
  const [target, setTarget] = useState(FAULT_TARGETS[1]);
  return (
    <form
      aria-label="Arm fault"
      className="flex flex-wrap items-end gap-2 rounded border p-3"
      onSubmit={(event) => {
        event.preventDefault();
        armed.mutate({ faultType, target });
      }}
    >
      <label className="flex flex-col gap-1">
        Fault type
        <select
          value={faultType}
          onChange={(event) => setFaultType(event.target.value)}
          className="rounded border px-2 py-1"
        >
          {FAULT_TYPES.map((type) => (
            <option key={type} value={type}>
              {type}
            </option>
          ))}
        </select>
      </label>
      <label className="flex flex-col gap-1">
        Target
        <select
          value={target}
          onChange={(event) => setTarget(event.target.value)}
          className="rounded border px-2 py-1"
        >
          {FAULT_TARGETS.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
      </label>
      <button
        type="submit"
        disabled={armed.isPending}
        className="rounded bg-amber-600 px-3 py-1 text-white disabled:opacity-50"
      >
        Arm fault
      </button>
      {armed.isSuccess && (
        <p className="w-full text-green-700">
          Armed {armed.data.fault_type} on {armed.data.target}.
        </p>
      )}
      {armed.isError && (
        <p role="alert" className="w-full text-red-700">
          {getErrorMessage(armed.error)}
        </p>
      )}
    </form>
  );
}

export function WorldControls() {
  const reset = useResetWorld();
  const seed = useSeedWorld();
  const [confirming, setConfirming] = useState<"reset" | null>(null);
  return (
    <div className="flex flex-col gap-2 rounded border p-3">
      <div className="flex gap-2">
        {confirming === "reset" ? (
          <>
            <span className="self-center">Reset wipes the world. Sure?</span>
            <button
              type="button"
              onClick={() => {
                reset.mutate();
                setConfirming(null);
              }}
              className="rounded bg-red-700 px-3 py-1 text-white"
            >
              Confirm reset
            </button>
            <button
              type="button"
              onClick={() => setConfirming(null)}
              className="rounded border px-3 py-1"
            >
              Cancel
            </button>
          </>
        ) : (
          <button
            type="button"
            onClick={() => setConfirming("reset")}
            className="rounded border border-red-700 px-3 py-1 text-red-700"
          >
            Reset world
          </button>
        )}
        <button
          type="button"
          disabled={seed.isPending}
          onClick={() => seed.mutate()}
          className="rounded border px-3 py-1 disabled:opacity-50"
        >
          Seed world
        </button>
      </div>
      {seed.isSuccess && (
        <p className="text-green-700">Seeded {JSON.stringify(seed.data.counts)}.</p>
      )}
      {seed.isError && (
        <p role="alert" className="text-red-700">
          {getErrorMessage(seed.error)}
        </p>
      )}
    </div>
  );
}
