import { describe, expect, it } from "vitest";
import { routePaths } from "@/app/router";

// Phase 1 smoke test: the single app exposes all four route shells.
describe("app router", () => {
  it("exposes /shop, /ops, /worker and /evaluation", () => {
    expect([...routePaths]).toEqual(["/shop", "/ops", "/worker", "/evaluation"]);
  });
});
