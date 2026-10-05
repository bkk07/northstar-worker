import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  MessageCircleQuestion,
  PackageX,
  RotateCcw,
  Truck,
} from "lucide-react";
import { useState } from "react";
import { useCreateTicket } from "../hooks/useShop";
import type { TicketFormState, TicketRead } from "../types";
import { ErrorState } from "@/shared/ui/feedback";
import { cn } from "@/shared/lib/utils";

const EMPTY: TicketFormState = { subject: "", body: "", category: "damage" };
const MAX_BODY = 2000;

const CATEGORIES = [
  {
    value: "damage",
    label: "Damage",
    hint: "Broken, cracked or defective item",
    icon: PackageX,
  },
  {
    value: "refund",
    label: "Refund",
    hint: "Charged wrong or want money back",
    icon: RotateCcw,
  },
  {
    value: "late_delivery",
    label: "Late",
    hint: "Order arrived past the promise date",
    icon: Truck,
  },
  {
    value: "general",
    label: "General",
    hint: "Anything else we can help with",
    icon: MessageCircleQuestion,
  },
] as const;

/**
 * Two-step raise-ticket wizard.
 * Step 1: category cards. Step 2: subject + details + submit.
 * The default category ("damage") is preselected so step 2 — with the
 * e2e-pinned fields Subject / What happened? / Raise ticket — renders
 * immediately; Back returns to step 1 to change category.
 */
export function TicketForm({
  customerCode,
  orderCode,
  onCreated,
}: {
  customerCode: string;
  orderCode?: string;
  onCreated: (ticket: TicketRead) => void;
}) {
  const [form, setForm] = useState<TicketFormState>(EMPTY);
  const [step, setStep] = useState<2 | 1>(2);
  const [succeeded, setSucceeded] = useState(false);
  const createTicket = useCreateTicket();
  const reduce = useReducedMotion();
  const activeCategory =
    CATEGORIES.find((c) => c.value === form.category) ?? CATEGORIES[0];

  const set =
    (field: keyof TicketFormState) =>
    (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
      setForm((prev) => ({ ...prev, [field]: event.target.value }));

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (createTicket.isPending) return;
    try {
      const ticket = await createTicket.mutateAsync({
        customer_code: customerCode,
        order_code: orderCode ?? null,
        ...form,
      });
      setSucceeded(true);
      // Brief success beat so the motion check reads before navigating.
      window.setTimeout(() => onCreated(ticket), reduce ? 0 : 550);
    } catch {
      // createTicket.isError renders the error state; nothing else to do.
    }
  }

  const slide = (dir: 1 | -1) =>
    reduce ? {} : { initial: { opacity: 0, x: 24 * dir }, animate: { opacity: 1, x: 0 }, exit: { opacity: 0, x: -24 * dir } };

  return (
    <form
      aria-label="Raise a ticket"
      onSubmit={handleSubmit}
      className="ns-card overflow-hidden"
    >
      <div className="ns-card-header">
        <div>
          <h2 className="ns-card-title">Raise a ticket</h2>
          <p className="ns-card-sub">
            Step {step} of 2 · {step === 1 ? "What kind of issue?" : "Tell us what happened"}
            {orderCode ? ` · for ${orderCode}` : ""}
          </p>
        </div>
        {/* Stepper */}
        <div aria-hidden className="flex items-center gap-1.5">
          {[1, 2].map((s) => (
            <span
              key={s}
              className={cn(
                "h-1.5 rounded-full transition-all",
                s < step
                  ? "w-6 bg-emerald-500"
                  : s === step
                    ? "w-6 bg-indigo-600"
                    : "w-3 bg-slate-200",
              )}
            />
          ))}
        </div>
      </div>

      <div className="ns-card-pad">
        <AnimatePresence mode="wait" initial={false}>
          {step === 1 ? (
            <motion.div
              key="step-1"
              {...slide(-1)}
              transition={{ duration: 0.25, ease: "easeOut" }}
            >
              <div role="radiogroup" aria-label="Issue category" className="grid grid-cols-2 gap-2.5">
                {CATEGORIES.map((cat) => {
                  const Icon = cat.icon;
                  const selected = form.category === cat.value;
                  return (
                    <button
                      key={cat.value}
                      type="button"
                      role="radio"
                      aria-checked={selected}
                      onClick={() => setForm((p) => ({ ...p, category: cat.value }))}
                      className={cn(
                        "flex flex-col items-start gap-1.5 rounded-2xl border p-3.5 text-left transition-colors",
                        selected
                          ? "border-indigo-600 bg-indigo-50/60 shadow-sm"
                          : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50",
                      )}
                    >
                      <span
                        className={cn(
                          "flex h-9 w-9 items-center justify-center rounded-xl",
                          selected ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-500",
                        )}
                      >
                        <Icon aria-hidden className="h-5 w-5" />
                      </span>
                      <span className="text-sm font-semibold text-slate-900">{cat.label}</span>
                      <span className="text-xs leading-4 text-slate-500">{cat.hint}</span>
                    </button>
                  );
                })}
              </div>
              <div className="mt-4 flex justify-end">
                <button
                  type="button"
                  onClick={() => setStep(2)}
                  className="ns-btn ns-btn-primary"
                >
                  Continue
                  <ArrowRight aria-hidden className="h-4 w-4" />
                </button>
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="step-2"
              {...slide(1)}
              transition={{ duration: 0.25, ease: "easeOut" }}
              className="space-y-3.5"
            >
              {/* Chosen category chip */}
              <div className="flex items-center gap-2 text-[13px]">
                <span className="inline-flex items-center gap-1.5 rounded-full border border-indigo-200 bg-indigo-50 px-2.5 py-1 font-medium text-indigo-800">
                  <activeCategory.icon aria-hidden className="h-3.5 w-3.5" />
                  {activeCategory.label}
                </span>
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  className="font-medium text-indigo-700 hover:underline"
                >
                  Change
                </button>
              </div>

              <div>
                <label htmlFor="ticket-subject" className="ns-label">
                  Subject
                </label>
                <input
                  id="ticket-subject"
                  value={form.subject}
                  onChange={set("subject")}
                  required
                  maxLength={140}
                  placeholder="e.g. Cracked screen on arrival"
                  className="ns-input"
                />
              </div>
              <div>
                <div className="flex items-baseline justify-between">
                  <label htmlFor="ticket-body" className="ns-label">
                    What happened?
                  </label>
                  <span
                    aria-live="polite"
                    className={cn(
                      "text-xs tabular-nums",
                      form.body.length > MAX_BODY - 100 ? "text-amber-600" : "text-slate-400",
                    )}
                  >
                    {form.body.length}/{MAX_BODY}
                  </span>
                </div>
                <textarea
                  id="ticket-body"
                  value={form.body}
                  onChange={set("body")}
                  required
                  rows={4}
                  maxLength={MAX_BODY}
                  aria-describedby="ticket-body-count"
                  placeholder="Describe the issue — what arrived, when, and photos if any…"
                  className="ns-input resize-y"
                />
                <span id="ticket-body-count" className="sr-only">
                  {form.body.length} of {MAX_BODY} characters used
                </span>
              </div>

              {createTicket.isError && <ErrorState message="Could not raise the ticket." />}

              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  className="ns-btn ns-btn-ghost ns-btn-sm"
                >
                  <ArrowLeft aria-hidden className="h-3.5 w-3.5" />
                  Back
                </button>
                <motion.button
                  type="submit"
                  disabled={createTicket.isPending || succeeded}
                  whileTap={reduce ? undefined : { scale: 0.97 }}
                  className={cn(
                    "ns-btn flex-1",
                    succeeded ? "bg-emerald-600 text-white" : "ns-btn-primary",
                  )}
                >
                  <AnimatePresence mode="wait" initial={false}>
                    {succeeded ? (
                      <motion.span
                        key="ok"
                        initial={reduce ? false : { scale: 0.4, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        transition={{ type: "spring", stiffness: 500, damping: 22 }}
                        className="inline-flex items-center gap-1.5"
                      >
                        <CheckCircle2 aria-hidden className="h-4 w-4" />
                        Ticket raised!
                      </motion.span>
                    ) : (
                      <motion.span key="idle">
                        {createTicket.isPending ? "Raising…" : "Raise ticket"}
                      </motion.span>
                    )}
                  </AnimatePresence>
                </motion.button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </form>
  );
}
