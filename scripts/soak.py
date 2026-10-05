"""Phase 29 chaos soak: fixed-seed task cycles through the real stack.

Picks N catalog scenarios with a seeded RNG (same seed, same set, same
order), drives each through the live stack with the eval harness (real
Runner, real HITL over HTTP), and fails on any safety violation: an
unexpected commit, a duplicate mutation, or a verifier false pass.
ERROR/TIMEOUT runs are reported as flakes (exit 2 when only flakes,
exit 1 on violations) so the flake rate stays visible separately.

Needs the live stack (backend 8000, MCP 8002, frontend on localhost)
and INCEPTION_API_KEY (loaded from `.env` like the eval harness).

Example: `python scripts/soak.py --seed 29 --tasks 6`
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for _path in (str(REPO_ROOT), str(REPO_ROOT / "common"), str(REPO_ROOT / "backend")):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from eval.eval import load_catalog  # noqa: E402
from eval.runner import Harness  # noqa: E402


def pick(seed: int, catalog: list[dict], count: int) -> list[dict]:
    """Seeded scenario sample, sorted for a stable run order."""
    rng = random.Random(seed)
    ids = sorted(rng.sample([row["id"] for row in catalog], min(count, len(catalog))))
    by_id = {row["id"]: row for row in catalog}
    return [by_id[sid] for sid in ids]


def main() -> int:
    """Drive the soak and exit 0/1/2 (clean/violations/flakes-only)."""
    parser = argparse.ArgumentParser(description="Fixed-seed chaos soak.")
    parser.add_argument("--seed", type=int, default=29, help="RNG seed (reproducibility)")
    parser.add_argument("--tasks", type=int, default=6, help="Scenario count")
    parser.add_argument("--catalog", default="", help="Catalog path (default: seeded)")
    parser.add_argument("--timeout", type=float, default=900.0, help="Seconds per scenario")
    parser.add_argument("--poll", type=float, default=2.0, help="HITL poll seconds")
    args = parser.parse_args()

    catalog = load_catalog(args.catalog or None)
    scenarios = pick(args.seed, catalog, args.tasks)
    print(f"soak seed={args.seed} tasks={[s['id'] for s in scenarios]}", flush=True)

    harness = Harness(
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8002",
        "local-operator-token",
        args.timeout,
        args.poll,
    )
    rows = []
    try:
        for scenario in scenarios:
            started = time.monotonic()
            score = harness.drive(scenario)
            rows.append(
                {
                    "id": scenario["id"],
                    "expected": scenario["expected_outcome"],
                    "actual": score.actual_outcome,
                    "ok": score.outcome_ok,
                    "unsafe": score.unsafe,
                    "duplicate": score.duplicate,
                    "false_pass": score.false_pass,
                    "runtime_s": round(time.monotonic() - started, 1),
                }
            )
            flag = "OK" if score.outcome_ok else "MISS"
            print(
                f"[{scenario['id']}] {flag} {score.actual_outcome} "
                f"unsafe={score.unsafe} dup={score.duplicate}",
                flush=True,
            )
    finally:
        harness.close()

    violations = [row for row in rows if row["unsafe"] or row["duplicate"] or row["false_pass"]]
    flakes = [
        row
        for row in rows
        if row["actual"] in ("ERROR", "TIMEOUT", "FAILED")
        and not (row["unsafe"] or row["duplicate"] or row["false_pass"])
    ]
    print(json.dumps({"seed": args.seed, "rows": rows}, indent=1))
    if violations:
        print(f"SOAK FAIL: {len(violations)} safety violations")
        return 1
    if flakes:
        print(f"SOAK FLAKY: {len(flakes)} non-violation misses")
        return 2
    print("SOAK CLEAN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
