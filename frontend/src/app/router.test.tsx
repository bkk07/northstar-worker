import { describe, expect, it } from "vitest";
import { routePaths } from "@/app/router";

// Shell smoke test: the single app exposes shop, ops, worker, products.
describe("app router", () => {
  it("exposes /shop, /ops, /worker and /products", () => {
    expect([...routePaths]).toEqual(["/shop", "/ops", "/worker", "/products"]);
  });
});
