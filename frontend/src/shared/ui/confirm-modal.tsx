import { motion, useReducedMotion } from "framer-motion";
import { TriangleAlert } from "lucide-react";
import { useEffect } from "react";

// Confirmation as a right slide-over (destructive ops mutations confirm
// first). Keeps role="alertdialog" + accessible names so e2e, unit tests,
// and the worker's a11y-driven browser all keep working.
export function ConfirmModal({
  title,
  body,
  confirmLabel,
  pending,
  onConfirm,
  onCancel,
}: {
  title: string;
  body: string;
  confirmLabel: string;
  pending: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const reduce = useReducedMotion();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !pending) onCancel();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onCancel, pending]);

  return (
    <div className="fixed inset-0 z-50">
      <div aria-hidden onClick={pending ? undefined : onCancel} className="absolute inset-0 bg-slate-950/45" />
      <motion.div
        role="alertdialog"
        aria-modal="true"
        aria-label={title}
        initial={reduce ? { opacity: 0 } : { opacity: 0, x: 360 }}
        animate={reduce ? { opacity: 1 } : { opacity: 1, x: 0 }}
        transition={reduce ? { duration: 0 } : { type: "tween", duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
        className="absolute right-0 top-0 flex h-full w-[min(420px,100vw)] flex-col bg-white shadow-2xl"
      >
        <div className="border-b border-slate-100 px-5 py-4">
          <p className="flex items-center gap-2 text-[15px] font-semibold tracking-tight">
            <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-amber-100 text-amber-700">
              <TriangleAlert aria-hidden className="h-4 w-4" />
            </span>
            {title}
          </p>
          <p className="mt-2 text-sm leading-6 text-slate-600">{body}</p>
        </div>
        <div className="mt-auto flex justify-end gap-2 border-t border-slate-100 bg-slate-50/70 px-5 py-4">
          <button
            type="button"
            onClick={onCancel}
            disabled={pending}
            className="ns-btn ns-btn-secondary"
          >
            Cancel
          </button>
          <motion.button
            type="button"
            onClick={onConfirm}
            disabled={pending}
            whileTap={reduce ? undefined : { scale: 0.97 }}
            className="ns-btn ns-btn-primary"
          >
            {pending ? "Working…" : confirmLabel}
          </motion.button>
        </div>
      </motion.div>
    </div>
  );
}
