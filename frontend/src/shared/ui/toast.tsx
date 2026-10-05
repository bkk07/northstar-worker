import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
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
  const reduce = useReducedMotion();
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
      <div
        role="status"
        aria-live="polite"
        className="fixed bottom-4 right-4 z-[60] w-[min(360px,calc(100vw-2rem))] space-y-2"
      >
        <AnimatePresence initial={false}>
          {toasts.map((toast) => (
            <motion.div
              key={toast.id}
              layout={reduce ? undefined : "position"}
              initial={reduce ? false : { opacity: 0, x: 80, scale: 0.96 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={reduce ? undefined : { opacity: 0, x: 40, scale: 0.97 }}
              transition={{ type: "spring", stiffness: 400, damping: 30 }}
              className="flex items-start gap-2.5 rounded-xl border border-slate-800 bg-slate-950 px-4 py-3 text-sm text-white shadow-pop"
            >
              <span aria-hidden className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-400" />
              {toast.message}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}
