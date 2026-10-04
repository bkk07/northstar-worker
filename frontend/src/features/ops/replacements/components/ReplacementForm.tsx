import { useState } from "react";
import { ConfirmModal } from "@/shared/ui/confirm-modal";
import { ErrorState } from "@/shared/ui/feedback";
import { useToast } from "@/shared/ui/toast";
import { getErrorMessage } from "@/shared/lib/errors";
import { useCreateReplacement } from "../hooks/useReplacements";
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
      <form aria-label="Create replacement" onSubmit={handleSubmit} className="space-y-2">
        <h3 className="font-semibold">New replacement</h3>
        <div>
          <label htmlFor="repl-order" className="block text-sm">
            Order code
          </label>
          <input
            id="repl-order"
            value={orderCode}
            onChange={(e) => setOrderCode(e.target.value)}
            required
            className="w-full rounded border px-2 py-1"
          />
        </div>
        <div>
          <label htmlFor="repl-sku" className="block text-sm">
            Item SKU
          </label>
          <input
            id="repl-sku"
            value={itemSku}
            onChange={(e) => setItemSku(e.target.value)}
            required
            className="w-full rounded border px-2 py-1"
          />
        </div>
        <button
          type="submit"
          disabled={create.isPending}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-50"
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
