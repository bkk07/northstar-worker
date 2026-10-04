import js from "@eslint/js";
import tseslint from "typescript-eslint";

// Phase 2: flat-config ESLint. JS recommended + TS recommended (without
// type-checking for speed); React-hooks rules arrive with feature phases.
export default tseslint.config(
  { ignores: ["dist", "coverage", "node_modules"] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
);
