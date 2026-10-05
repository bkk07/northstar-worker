"""Eval CLI: run the seeded suite through the real stack (Phase 27).

Flow per scenario (§26): reset → seed → arm the fault plan → submit
through the real API → answer approvals/clarifications through the
public endpoints → wait for terminal → query the oracle → score.
Reports land in `eval/reports/<ts>.json`/`.md` with mean and min over
repeats for the headline numbers.

Needs backend + MCP up (and a frontend for browser scenarios); use
`--with-servers` to boot them, or run them yourself first.
INCEPTION_API_KEY must be set for live runs.

Usage: python eval/eval.py --suite seeded --repeat 3
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from eval.metrics import aggregate  # noqa: E402
from eval.report import save_reports  # noqa: E402
from eval.runner import Harness, load_catalog  # noqa: E402

INJECTION_IDS = {"S5", "S38", "S39"}


def _load_env() -> None:
    env_file = REPO_ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            name, _, value = line.partition("=")
            os.environ.setdefault(name.strip(), value.strip())


def _wait_healthy(url: str, timeout_s: float = 120.0) -> None:
    """Poll /api/health until ready (fail fast with a clear message)."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            if httpx.get(f"{url}/api/health", timeout=3).status_code == 200:
                return
        except httpx.HTTPError:
            time.sleep(2)
    raise RuntimeError(f"server at {url} never became healthy (start it or pass --with-servers)")


def _start_servers(backend_port: int, mcp_port: int, frontend_port: int) -> list[subprocess.Popen]:
    """Boot backend + MCP + frontend (terminated at the end of the run)."""
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        (str(REPO_ROOT), str(REPO_ROOT / "backend"), str(REPO_ROOT / "common"))
    )
    env["MCP_PORT"] = str(mcp_port)
    env["FRONTEND_URL"] = f"http://localhost:{frontend_port}"
    backend = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--app-dir",
            str(REPO_ROOT / "backend"),
            "--port",
            str(backend_port),
        ],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    mcp = subprocess.Popen(
        [sys.executable, "-m", "mcp_server.server"],
        cwd=str(REPO_ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    frontend = subprocess.Popen(
        ["npm", "run", "dev", "--", "--port", str(frontend_port), "--strictPort"],
        cwd=str(REPO_ROOT / "frontend"),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return [backend, mcp, frontend]


def main() -> None:
    """Parse flags, run repeats, aggregate, report, optionally record."""
    parser = argparse.ArgumentParser(description="Run the eval suite through the real stack.")
    parser.add_argument("--suite", default="seeded", help="Suite name for the report")
    parser.add_argument("--scenarios", default="", help="Comma ids (default: whole catalog)")
    parser.add_argument("--repeat", type=int, default=1, help="Repeats (mean and min reported)")
    parser.add_argument("--backend", default="http://127.0.0.1:8000", help="Backend URL")
    parser.add_argument("--mcp-url", default="http://127.0.0.1:8002", help="MCP URL")
    parser.add_argument("--operator-token", default="local-operator-token", help="Control token")
    parser.add_argument(
        "--scenario-timeout", type=float, default=1500.0, help="Seconds per scenario"
    )
    parser.add_argument("--with-servers", action="store_true", help="Boot backend+MCP+frontend")
    parser.add_argument("--record", action="store_true", help="POST the report to /api/eval/runs")
    args = parser.parse_args()

    _load_env()
    servers: list[subprocess.Popen] = []
    try:
        if args.with_servers:
            servers = _start_servers(8000, 8002, 5173)
        _wait_healthy(args.backend)
        catalog = load_catalog()
        wanted = {s.strip() for s in args.scenarios.split(",") if s.strip()}
        scenarios = [s for s in catalog if not wanted or s["id"] in wanted]
        print(f"suite={args.suite} scenarios={len(scenarios)} repeat={args.repeat}", flush=True)

        harness = Harness(args.backend, args.mcp_url, args.operator_token, args.scenario_timeout)
        all_scores = []
        try:
            for round_no in range(args.repeat):
                for scenario in scenarios:
                    print(f"[{scenario['id']}] running...", flush=True)
                    score = harness.drive(scenario)
                    all_scores.append((round_no, score))
                    mark = "OK" if score.outcome_ok else "MISS"
                    print(f"[{scenario['id']}] {mark} {score.actual_outcome}", flush=True)
        finally:
            harness.close()

        by_round = {}
        for round_no, score in all_scores:
            by_round.setdefault(round_no, []).append(score)
        round_metrics = [aggregate(scores, INJECTION_IDS) for _, scores in sorted(by_round.items())]
        metrics = _mean_min(round_metrics)
        flat = [score for _, score in all_scores]
        notes = {
            "human_intervention_rate": "compare with oracle-expected parks",
            "avg_tool_calls": "mean over repeats",
        }
        saved = save_reports(
            args.suite,
            metrics,
            flat,
            notes,
            extra_notes=[f"repeat={args.repeat}; headlines are means over repeats"],
        )
        print(f"report: {saved['markdown']}")
        if args.record:
            _record(args.backend, args.suite, metrics, flat, saved["document"])
    finally:
        for proc in servers:
            proc.terminate()
        for proc in servers:
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()


def _mean_min(round_metrics: list[dict]) -> dict:
    """Mean across repeats (min folded into scenario notes when repeated)."""
    if len(round_metrics) == 1:
        return round_metrics[0]
    keys = [k for k in round_metrics[0] if k != "scenarios"]
    merged = {"scenarios": round_metrics[0]["scenarios"], "repeats": len(round_metrics)}
    for key in keys:
        values = [m[key] for m in round_metrics if m[key] is not None]
        merged[key] = sum(values) / len(values) if values else None
        mins = [m[key] for m in round_metrics if isinstance(m[key], (int, float))]
        if mins:
            merged[f"{key}_min"] = min(mins)
    return merged


def _record(backend: str, suite: str, metrics: dict, scores, document: str) -> None:
    """POST the report to the evaluation API (same table in /evaluation)."""
    from dataclasses import asdict

    response = httpx.post(
        f"{backend}/api/eval/runs",
        json={
            "suite": suite,
            "scenario_count": metrics.get("scenarios", 0),
            "metrics": metrics,
            "results": [
                {
                    "scenario_id": s.scenario_id,
                    "expected_outcome": s.expected_outcome,
                    "actual_outcome": s.actual_outcome,
                    "outcome_ok": s.outcome_ok,
                    "scores": asdict(s),
                }
                for s in scores
            ],
            "report_md": document,
        },
        timeout=30,
    )
    response.raise_for_status()
    print(f"recorded eval run {response.json()['id']}")


if __name__ == "__main__":
    main()
