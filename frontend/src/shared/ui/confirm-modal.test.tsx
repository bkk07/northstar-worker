import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ConfirmModal } from "@/shared/ui/confirm-modal";

describe("ConfirmModal", () => {
  it("confirms and cancels with accessible names", () => {
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    render(
      <ConfirmModal
        title="Confirm refund"
        body="Refund Rs. 100.00?"
        confirmLabel="Create refund"
        pending={false}
        onConfirm={onConfirm}
        onCancel={onCancel}
      />,
    );
    expect(screen.getByRole("alertdialog", { name: "Confirm refund" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Create refund" }));
    expect(onConfirm).toHaveBeenCalledOnce();
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it("disables confirm while pending", () => {
    render(
      <ConfirmModal
        title="Confirm refund"
        body="Refund?"
        confirmLabel="Create refund"
        pending
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByRole("button", { name: "Working…" })).toBeDisabled();
  });
});
