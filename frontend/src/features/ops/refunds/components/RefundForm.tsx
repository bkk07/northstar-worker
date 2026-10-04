import { useState } from "react";
import { ConfirmModal } from "@/shared/ui/confirm-modal";
import { ErrorState } from "@/shared/ui/feedback";
import { useToast } from "@/shared/ui/toast";
import { getErrorMessage } from "@/shared/lib/errors";
import { useCreateRefund } from "../hooks/useRefunds";
import type { RefundRead } from "../../types";

function rupeesToPaise(value: string): number | null {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed <= 0) return null;
  return Math.round(parsed * 100);
}

export function RefundForm({
  ticketCode,
  onCreated,
}: {
  ticketCode: string;
  onCreated: (refund: RefundRead) => void;
}) {
  const [orderCode, setOrderCode] = useState("");
  const [amount, setAmount] = useState("");
  const [confirming, setConfirming] = useState(false);
  const create = useCreateRefund();
  const toast = useToast();
  const paise = rupeesToPaise(amount);

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (paise !== null) setConfirming(true);
  }

  async function handleConfirm() {
    if (paise === null) return;
    try {
      const refund = await create.mutateAsync({
        order_code: orderCode,
        ticket_code: ticketCode,
        amount_paise: paise,
      });
      setConfirming(false);
      toast.push(`Refund ${refund.id} created.`);
      onCreated(refund);
    } catch {
      setConfirming(false);
    }
  }

  return (
    <div>
      <form aria-label="Create refund" onSubmit={handleSubmit} className="space-y-2">
        <h3 className="font-semibold">New refund</h3>
        <div>
          <label htmlFor="refund-order" className="block text-sm">
            Order code
          </label>
          <input
            id="refund-order"
            value={orderCode}
            onChange={(e) => setOrderCode(e.target.value)}
            required
            className="w-full rounded border px-2 py-1"
          />
        </div>
        <div>
          <label htmlFor="refund-amount" className="block text-sm">
            Amount (Rs.)
          </label>
          <input
            id="refund-amount"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            required
            inputMode="decimal"
            placeholder="2500.00"
            className="w-full rounded border px-2 py-1"
          />
        </div>
        <button
          type="submit"
          disabled={create.isPending || paise === null}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-50"
        >
          Review refund
        </button>
      </form>
      {confirming && paise !== null && (
        <ConfirmModal
          title="Confirm refund"
          body={`Refund Rs. ${(paise / 100).toFixed(2)} on ${orderCode}?`}
          confirmLabel="Create refund"
          pending={create.isPending}
          onConfirm={handleConfirm}
          onCancel={() => setConfirming(false)}
        />
      )}
      {create.isError && !confirming && <ErrorState message={getErrorMessage(create.error)} />}
    </div>
  );
}
