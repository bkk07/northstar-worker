import { createContext, useCallback, useContext, useState } from "react";

export interface Toast {
  id: number;
  message: string;
}

const ToastContext = createContext<{ push: (message: string) => void }>({
  push: () => {},
});

// Toast notifications (inline errors stay in pages; toasts announce results).
export function useToast() {
  return useContext(ToastContext);
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const push = useCallback((message: string) => {
    const id = Date.now() + Math.random();
    setToasts((current) => [...current, { id, message }]);
    window.setTimeout(() => {
      setToasts((current) => current.filter((toast) => toast.id !== id));
    }, 5000);
  }, []);

  return (
    <ToastContext.Provider value={{ push }}>
      {children}
      <div role="status" aria-live="polite" className="fixed bottom-4 right-4 space-y-2">
        {toasts.map((toast) => (
          <div key={toast.id} className="rounded bg-slate-900 px-4 py-2 text-sm text-white">
            {toast.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
