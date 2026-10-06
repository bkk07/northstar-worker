import { create } from "zustand";

export type ToastTone = "ok" | "info" | "bad";

export type Toast = { id: number; message: string; tone: ToastTone };

type ToastState = {
  toasts: Toast[];
  push: (message: string, tone?: ToastTone) => void;
  dismiss: (id: number) => void;
};

let nextId = 1;

/** Lightweight global toasts for customer confirmations and failures. */
export const useToast = create<ToastState>((set) => ({
  toasts: [],
  push: (message, tone = "info") => {
    const id = nextId++;
    set((s) => ({ toasts: [...s.toasts.slice(-2), { id, message, tone }] }));
    window.setTimeout(() => {
      set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) }));
    }, 4200);
  },
  dismiss: (id) =>
    set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}));

export const toast = {
  ok: (message: string) => useToast.getState().push(message, "ok"),
  info: (message: string) => useToast.getState().push(message, "info"),
  bad: (message: string) => useToast.getState().push(message, "bad"),
};
