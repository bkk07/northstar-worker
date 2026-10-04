import { execSync } from "node:child_process";
import path from "node:path";

// Pristine seeded world before every e2e run: specs use fixed seeded
// entities (no per-run unique data needed) and stay re-runnable.
export default async function globalSetup() {
  const root = path.resolve(import.meta.dirname, "..");
  execSync("python -m database.seeds.loader reset", { cwd: root, stdio: "inherit" });
  execSync("python -m database.seeds.loader seed", { cwd: root, stdio: "inherit" });
}
