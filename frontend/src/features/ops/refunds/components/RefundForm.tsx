import { HandCoins } from "lucide-react";
import { useState } from "react";
import { ConfirmModal } from "@/shared/ui/confirm-modal";
import { ErrorState } from "@/shared/ui/feedback";
import { useToast } from "@/shared/ui/toast";
import { getErrorMessage } from "@/shared/lib/errors";
import { useCreateRefund } from "../hooks/useRefunds";
import { useUiFlags } from "../../tickets/hooks/useTickets";
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
  // DOM_DRIFT fault: labels renamed, amount field moves first.
  const drift = useUiFlags().data?.dom_drift === true;
  const orderLabel = drift ? "Order reference" : "Order code";
  const amountLabel = drift ? "Refund total (Rs.)" : "Amount (Rs.)";

  const orderField = (
    <div>
      <label htmlFor="refund-order" className="ns-label">
        {orderLabel}
      </label>
      <input
        id="refund-order"
        value={orderCode}
        onChange={(e) => setOrderCode(e.target.value)}
        required
        placeholder="ORD-1942"
        autoComplete="off"
        className="ns-input"
      />
    </div>
  );
  const amountField = (
    <div>
      <label htmlFor="refund-amount" className="ns-label">
        {amountLabel}
      </label>
      <input
        id="refund-amount"
        value={amount}
        onChange={(e) => setAmount(e.target.value)}
        required
        inputMode="decimal"
        placeholder="2500.00"
        autoComplete="off"
        className="ns-input"
      />
    </div>
  );

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
      <form aria-label="Create refund" onSubmit={handleSubmit} className="space-y-3">
        <h3 className="flex items-center gap-2 text-sm font-semibold tracking-tight">
          <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700">
            <HandCoins aria-hidden className="h-4 w-4" />
          </span>
          New refund
        </h3>
        {drift ? (
          <>
            {amountField}
            {orderField}
          </>
        ) : (
          <>
            {orderField}
            {amountField}
          </>
        )}
        <button
          type="submit"
          disabled={create.isPending || paise === null}
          className="ns-btn ns-btn-primary"
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
