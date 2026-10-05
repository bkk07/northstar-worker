"""Generalization reporting: freeze diff, seal, seeded vs held-out (Phase 28).

The core (`agent/graph`, `agent/nodes`, `agent/failures`,
`mcp_server/tools`, `browser/`) froze at the `eval-core-freeze` tag:
any diff since then is counted and must be a documented fix. Task
support lands outside the core (registry, contract, policy extensions)
and is listed as task-specific extensions. The held-out catalog is
sealed with a sha256 hash; the seal test fails loudly on tampering.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
HELD_OUT_CATALOG = REPO_ROOT / "eval" / "held_out" / "catalog.yaml"
SEAL_FILE = REPO_ROOT / "eval" / "held_out" / "SEALED_SHA256"
FREEZE_TAG = "eval-core-freeze"

CORE_DIRS = (
    "agent/graph",
    "agent/nodes",
    "agent/failures",
    "mcp_server/tools",
    "browser",
)


def seal_catalog(path: Path | None = None) -> str:
    """sha256 of the held-out catalog (the seal value)."""
    target = path or HELD_OUT_CATALOG
    return hashlib.sha256(target.read_bytes()).hexdigest()


def verify_seal() -> bool:
    """The catalog still matches its committed seal (tamper-evident)."""
    if not SEAL_FILE.exists():
        return False
    sealed = SEAL_FILE.read_text(encoding="utf-8").strip().split()[0]
    return sealed == seal_catalog()


def core_diff(tag: str = FREEZE_TAG) -> dict:
    """Changed lines per core dir since the freeze tag (docs fixes separately)."""
    per_dir: dict[str, int] = {}
    files: list[str] = []
    for core in CORE_DIRS:
        proc = subprocess.run(
            ["git", "diff", "--numstat", tag, "HEAD", "--", core],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
        total = 0
        for line in proc.stdout.splitlines():
            added, deleted, name = (line.split("\t") + ["", "", ""])[:3]
            try:
                total += int(added) + int(deleted)
            except ValueError:
                continue
            files.append(name)
        per_dir[core] = total
    return {"per_dir": per_dir, "files": sorted(set(files)), "total": sum(per_dir.values())}


def comparison_table(seeded: dict, held_out: dict) -> list[dict]:
    """Seeded vs held-out rows for the generalization report."""
    names = [name for name, _ in _metric_order(seeded, held_out)]
    rows = []
    for name in names:
        left, right = seeded.get(name), held_out.get(name)
        delta = None
        if isinstance(left, (int, float)) and isinstance(right, (int, float)):
            delta = right - left
        rows.append({"metric": name, "seeded": left, "held_out": right, "delta": delta})
    return rows


def _metric_order(seeded: dict, held_out: dict) -> list[tuple[str, str]]:
    """Report order follows the §26 table (extra keys appended)."""
    try:
        from eval.metrics import METRIC_TARGETS
    except ImportError:
        METRIC_TARGETS = ()
    order = [name for name, _ in METRIC_TARGETS]
    extra = [k for k in list(seeded) + list(held_out) if k not in order and k != "scenarios"]
    return [(name, "") for name in order + extra]


def render_generalization_markdown(
    seeded: dict,
    held_out: dict,
    diff: dict,
    extensions: list[str] | None = None,
    fixes: list[str] | None = None,
) -> str:
    """Seeded vs held-out table plus the core-change count."""
    lines = [
        "# Generalization report (Phase 28)",
        "",
        f"Seeded scenarios: {seeded.get('scenarios', '?')} · "
        f"held-out scenarios: {held_out.get('scenarios', '?')}",
        "",
        "## Seeded vs held-out",
        "",
        "| Metric | Seeded | Held-out | Delta |",
        "|---|---|---|---|",
    ]
    for row in comparison_table(seeded, held_out):
        lines.append(
            f"| {row['metric']} | {_cell(row['seeded'], row['metric'])} | "
            f"{_cell(row['held_out'], row['metric'])} | "
            f"{_delta_cell(row['delta'], row['metric'])} |"
        )
    lines += [
        "",
        "## Core diff since freeze",
        "",
        f"Changed lines: {diff['total']} (target: 0 except documented fixes)",
    ]
    for core, count in diff["per_dir"].items():
        lines.append(f"- {core}: {count}")
    if diff["files"]:
        lines.append(f"- files: {', '.join(diff['files'])}")
    lines += ["", "## Task-specific extensions", ""]
    for extension in extensions or ["(none)"]:
        lines.append(f"- {extension}")
    lines += ["", "## Documented core fixes", ""]
    for fix in fixes or ["(none)"]:
        lines.append(f"- {fix}")
    lines.append("")
    return "\n".join(lines)


def _cell(value, name: str = "") -> str:
    """Compact cell: percents for rates, rounded means, n/a for missing."""
    if value is None:
        return "n/a"
    if name == "delta":
        return _delta_cell(value)
    if isinstance(value, float):
        if name.startswith("avg_"):
            return f"{value:.1f}"
        return f"{value:.1%}" if 0.0 <= value <= 1.0 else f"{value:.1f}"
    return str(value)


def _delta_cell(value, metric: str = "") -> str:
    """Signed delta: percent for rates, one decimal for means."""
    if value is None:
        return "n/a"
    if isinstance(value, float):
        if metric.startswith("avg_"):
            return f"{value:+.1f}"
        return f"{value:+.1%}"
    return str(value)
