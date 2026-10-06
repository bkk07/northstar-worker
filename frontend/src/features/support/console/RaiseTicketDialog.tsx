import { useState } from "react";
import { TicketForm } from "@/features/shop/components/TicketForm";
import type { TicketRead } from "@/features/shop/types";
import { SlideOver } from "@/shared/ui/slide-over";

/**
 * Raise-ticket drawer: customer + optional order, then the pinned
 * two-step form (Subject / What happened? / Raise ticket stay intact).
 */
export function RaiseTicketDialog({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: (ticket: TicketRead) => void;
}) {
  const [customerCode, setCustomerCode] = useState("C102");
  const [orderCode, setOrderCode] = useState("");

  return (
    <SlideOver
      open={open}
      onClose={onClose}
      label="Raise a ticket"
      title="Raise a ticket"
      desc="The bot can pick it up the moment it exists."
    >
      <div className="flex flex-col gap-3">
        <div className="grid grid-cols-2 gap-2">
          <label className="flex flex-col gap-1 text-[13px] font-medium text-slate-700">
            Customer code
            <input
              value={customerCode}
              onChange={(event) => setCustomerCode(event.target.value)}
              placeholder="C102"
              className="ns-input"
            />
          </label>
          <label className="flex flex-col gap-1 text-[13px] font-medium text-slate-700">
            Order code (optional)
            <input
              value={orderCode}
              onChange={(event) => setOrderCode(event.target.value)}
              placeholder="ORD-1943"
              className="ns-input"
            />
          </label>
        </div>
        {customerCode.trim() && (
          <TicketForm
            key={`${customerCode.trim()}-${orderCode.trim()}`}
            customerCode={customerCode.trim()}
            orderCode={orderCode.trim() || undefined}
            onCreated={onCreated}
          />
        )}
      </div>
    </SlideOver>
  );
}
