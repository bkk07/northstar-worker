import { PackagePlus } from "lucide-react";
import { useState } from "react";
import { ConfirmModal } from "@/shared/ui/confirm-modal";
import { ErrorState } from "@/shared/ui/feedback";
import { useToast } from "@/shared/ui/toast";
import { getErrorMessage } from "@/shared/lib/errors";
import { useCreateReplacement } from "../hooks/useReplacements";
import { useUiFlags } from "../../tickets/hooks/useTickets";
import type { ReplacementRead } from "../../types";

export function ReplacementForm({
  ticketCode,
  onCreated,
}: {
  ticketCode: string;
  onCreated: (replacement: ReplacementRead) => void;
}) {
  const [orderCode, setOrderCode] = useState("");
  const [itemSku, setItemSku] = useState("");
  const [confirming, setConfirming] = useState(false);
  const create = useCreateReplacement();
  const toast = useToast();
  // DOM_DRIFT fault (S25): labels renamed and fields reordered. Accessible
  // names still exist (a11y holds); only the text/position changes, which is
  // what forces the worker to re-discover instead of replaying stale refs.
  const drift = useUiFlags().data?.dom_drift === true;
  const orderLabel = drift ? "Order reference" : "Order code";
  const skuLabel = drift ? "Stock-keeping code" : "Item SKU";

  const orderField = (
    <div>
      <label htmlFor="repl-order" className="ns-label">
        {orderLabel}
      </label>
      <input
        id="repl-order"
        value={orderCode}
        onChange={(e) => setOrderCode(e.target.value)}
        required
        placeholder="ORD-1942"
        autoComplete="off"
        className="ns-input"
      />
    </div>
  );
  const skuField = (
    <div>
      <label htmlFor="repl-sku" className="ns-label">
        {skuLabel}
      </label>
      <input
        id="repl-sku"
        value={itemSku}
        onChange={(e) => setItemSku(e.target.value)}
        required
        placeholder="CB-05"
        autoComplete="off"
        className="ns-input"
      />
    </div>
  );

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setConfirming(true);
  }

  async function handleConfirm() {
    try {
      const replacement = await create.mutateAsync({
        order_code: orderCode,
        item_sku: itemSku,
        ticket_code: ticketCode,
      });
      setConfirming(false);
      toast.push(`Replacement ${replacement.id} created.`);
      onCreated(replacement);
    } catch {
      setConfirming(false);
    }
  }

  return (
    <div>
      <form aria-label="Create replacement" onSubmit={handleSubmit} className="space-y-3">
        <h3 className="flex items-center gap-2 text-sm font-semibold tracking-tight">
          <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-indigo-50 text-indigo-700">
            <PackagePlus aria-hidden className="h-4 w-4" />
          </span>
          New replacement
        </h3>
        {drift ? (
          <>
            {skuField}
            {orderField}
          </>
        ) : (
          <>
            {orderField}
            {skuField}
          </>
        )}
        <button
          type="submit"
          disabled={create.isPending}
          className="ns-btn ns-btn-primary"
        >
          Review replacement
        </button>
      </form>
      {confirming && (
        <ConfirmModal
          title="Confirm replacement"
          body={`Ship a replacement for ${itemSku} on ${orderCode}?`}
          confirmLabel="Create replacement"
          pending={create.isPending}
          onConfirm={handleConfirm}
          onCancel={() => setConfirming(false)}
        />
      )}
      {create.isError && !confirming && <ErrorState message={getErrorMessage(create.error)} />}
    </div>
  );
}
