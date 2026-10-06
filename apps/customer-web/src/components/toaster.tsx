import { CheckCircle2, Info, X, XCircle } from "lucide-react";
import { useToast, type ToastTone } from "@/stores/toast-store";

const toneIcon: Record<ToastTone, typeof Info> = {
  ok: CheckCircle2,
  info: Info,
  bad: XCircle,
};

/** Fixed bottom-right toast stack; mounted once in the app shell. */
export function Toaster() {
  const toasts = useToast((s) => s.toasts);
  const dismiss = useToast((s) => s.dismiss);
  return (
    <div className="ns-toasts" role="status" aria-live="polite">
      {toasts.map((t) => {
        const Icon = toneIcon[t.tone];
        return (
          <div key={t.id} className={`ns-toast ns-toast-${t.tone}`}>
            <Icon size={16} aria-hidden />
            <span className="ns-toast-msg">{t.message}</span>
            <button
              className="ns-toast-x"
              aria-label="Dismiss notification"
              onClick={() => dismiss(t.id)}
            >
              <X size={14} aria-hidden />
            </button>
          </div>
        );
      })}
    </div>
  );
}
