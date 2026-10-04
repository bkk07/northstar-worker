import { describe, expect, it } from "vitest";
import { formatINR } from "@/shared/lib/format";

// Mirrors the backend money tests (common.money.format_inr).
describe("formatINR", () => {
  it("formats paise with Indian grouping", () => {
    expect(formatINR(250000)).toBe("₹2,500.00");
    expect(formatINR(15000000)).toBe("₹1,50,000.00");
    expect(formatINR(1000000000)).toBe("₹1,00,00,000.00");
    expect(formatINR(999)).toBe("₹9.99");
  });

  it("handles zero and negatives", () => {
    expect(formatINR(0)).toBe("₹0.00");
    expect(formatINR(-150)).toBe("-₹1.50");
  });
});
