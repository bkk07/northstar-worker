export function LoadingState({ what }: { what: string }) {
  return (
    <p role="status" className="p-4 text-sm text-slate-600">
      Loading {what}…
    </p>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="rounded-md bg-red-50 p-4 text-sm text-red-800">
      <p>Something went wrong: {message}</p>
      {onRetry && (
        <button type="button" onClick={onRetry} className="mt-2 underline">
          Retry
        </button>
      )}
    </div>
  );
}
