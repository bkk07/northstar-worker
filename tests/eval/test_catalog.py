"""Phase 5: catalogue expectations are oracle-derived; oracle is independent."""

import ast
from pathlib import Path

import yaml

from eval.oracle_rules import derive_expected, load_thresholds

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOG = yaml.safe_load((REPO_ROOT / "eval" / "scenarios" / "catalog.yaml").read_text())
POLICIES = yaml.safe_load((REPO_ROOT / "database" / "seeds" / "policies.yaml").read_text())


def test_forty_scenarios_in_catalogue():
    """About 40 scenarios (ids S1..S40, held-out range untouched)."""
    assert len(CATALOG) == 40
    assert [s["id"] for s in CATALOG] == [f"S{i}" for i in range(1, 41)]


def test_every_scenario_has_oracle_derived_expectation():
    """Catalogue expected_* must equal the independent oracle derivation."""
    thresholds = load_thresholds(POLICIES)
    for scn in CATALOG:
        verdict = derive_expected(scn, scn.get("intended_effects", []), thresholds)
        assert verdict.outcome == scn["expected_outcome"], scn["id"]
        assert [dict(e) for e in verdict.effects] == scn["expected_effects"], scn["id"]


def test_effect_tickets_match_scenario_ticket():
    """No effect may point at another scenario's ticket."""
    for scn in CATALOG:
        for effect in scn.get("intended_effects", []) + scn.get("expected_effects", []):
            assert effect["ticket_code"] == scn["ticket_code"], scn["id"]


def test_oracle_imports_nothing_from_agent():
    """The oracle is independent truth: no agent imports, ever."""
    tree = ast.parse((REPO_ROOT / "eval" / "oracle_rules.py").read_text())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert "agent" not in imported
