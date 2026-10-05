"""Eval reports: JSON + markdown with the §26 metrics table (Phase 27).

The report has the columns Metric, Result, Target, Notes; per-scenario
rows follow for drilldown. Saved under `eval/reports/<ts>.json`/`.md`
and POSTed to `/api/eval/runs` when recording is on.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from eval.metrics import METRIC_TARGETS, ScenarioScore

REPORTS_DIR = Path(__file__).resolve().parent / "reports"


RATE_METRICS = frozenset(
    {
        "task_success_rate",
        "decision_accuracy",
        "recovery_success_rate",
        "verification_accuracy",
        "unsafe_action_rate",
        "duplicate_mutation_rate",
        "human_intervention_rate",
        "over_escalation_rate",
        "unsafe_under_escalation_rate",
        "budget_exhaustion_rate",
        "verifier_false_pass_rate",
        "injection_success_rate",
    }
)


def _format_value(name: str, value) -> str:
    """Rates as percent, means rounded, None as n/a."""
    if value is None:
        return "n/a"
    if name in RATE_METRICS and isinstance(value, float):
        return f"{value:.1%}"
    if isinstance(value, float):
        return f"{value:.1f}"
    return str(value)


def metric_rows(metrics: dict, notes: dict[str, str] | None = None) -> list[dict]:
    """Metric/Result/Target/Notes rows for the §26 table."""
    notes = notes or {}
    return [
        {
            "metric": name,
            "result": _format_value(name, metrics.get(name)),
            "target": target,
            "notes": notes.get(name, ""),
        }
        for name, target in METRIC_TARGETS
    ]


def render_markdown(
    suite: str,
    started_at: str,
    metrics: dict,
    scores: list[ScenarioScore],
    notes: dict[str, str] | None = None,
    extra_notes: list[str] | None = None,
) -> str:
    """Full report document (the same table appears in `/evaluation`)."""
    lines = [
        f"# Evaluation report: {suite}",
        "",
        f"Started: {started_at} · scenarios: {metrics.get('scenarios', 0)}",
        "",
        "## Metrics (§26)",
        "",
        "| Metric | Result | Target | Notes |",
        "|---|---|---|---|",
    ]
    for row in metric_rows(metrics, notes):
        lines.append(f"| {row['metric']} | {row['result']} | {row['target']} | {row['notes']} |")
    lines += ["", "## Scenarios", ""]
    for score in scores:
        flag = "OK" if score.outcome_ok else "MISS"
        lines.append(
            f"- {flag} {score.scenario_id}: expected {score.expected_outcome}, "
            f"got {score.actual_outcome}" + ("" if score.outcome_ok else _score_detail(score))
        )
    if extra_notes:
        lines += ["", "## Analysis", ""]
        lines += [f"- {note}" for note in extra_notes]
    lines.append("")
    return "\n".join(lines)


def _score_detail(score: ScenarioScore) -> str:
    """Why a scenario missed (decision, safety, or harness error)."""
    bits = []
    if score.decision_ok is False:
        bits.append("wrong policy decision")
    if score.unsafe:
        bits.append("UNSAFE action")
    if score.duplicate:
        bits.append("duplicate mutation")
    if score.over_escalated:
        bits.append("over-escalated")
    if score.under_escalated:
        bits.append("UNDER-escalated")
    if score.verification_ok is False:
        bits.append("verifier disagrees with state")
    if score.unsafe and score.committed:
        bits.append(f"committed {score.committed}")
    if score.policy_outcome:
        bits.append(f"policy={score.policy_outcome}")
    if score.error:
        bits.append(score.error)
    return f" ({'; '.join(bits)})" if bits else ""


def save_reports(
    suite: str, metrics: dict, scores: list[ScenarioScore], notes=None, extra_notes=None
) -> dict:
    """Write `<ts>.json` + `.md` under `eval/reports/`; return paths + doc."""
    started = datetime.now(UTC).replace(microsecond=0).isoformat()
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "suite": suite,
        "started_at": started,
        "metrics": metrics,
        "scores": [asdict(score) for score in scores],
    }
    markdown = render_markdown(suite, started, metrics, scores, notes, extra_notes)
    json_path = REPORTS_DIR / f"{stamp}.json"
    md_path = REPORTS_DIR / f"{stamp}.md"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md_path.write_text(markdown, encoding="utf-8", newline="\n")
    return {
        "json": str(json_path),
        "markdown": str(md_path),
        "document": markdown,
        "payload": payload,
    }
