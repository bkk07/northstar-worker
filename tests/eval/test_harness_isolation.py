"""Harness isolation: the oracle never touches the agent; HITL stays public.

The oracle is independent truth — `eval/oracle_rules.py` and
`eval/oracle_client.py` must not import the agent, the backend app, or
the database. The driver (`eval/runner.py`) may execute through the
in-process Runner, but approvals and clarifications go through the
public HTTP endpoints only: no service or database imports there.
"""

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = REPO_ROOT / "eval"

FORBIDDEN_EVERYWHERE = {"agent", "app", "database", "mcp_server", "backend", "verifier"}
FORBIDDEN_RUNNER = {"app", "database", "mcp_server", "backend"}


def _imports_of(path: Path) -> set[str]:
    """Top-level packages imported anywhere in the file."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    return imported


def test_oracle_modules_import_no_agent_stack():
    """Independent truth: oracle code never touches agent/app/database."""
    for name in ("oracle_rules.py", "oracle_client.py", "metrics.py", "report.py"):
        imported = _imports_of(EVAL_DIR / name)
        assert not (imported & FORBIDDEN_EVERYWHERE), (name, imported & FORBIDDEN_EVERYWHERE)


def test_eval_cli_imports_no_agent_stack():
    """The CLI orchestrates; it never reaches into the stack."""
    imported = _imports_of(EVAL_DIR / "eval.py")
    assert not (imported & FORBIDDEN_EVERYWHERE), imported & FORBIDDEN_EVERYWHERE


def test_runner_uses_no_backend_or_database():
    """The driver executes in-process but persists nothing itself."""
    imported = _imports_of(EVAL_DIR / "runner.py")
    assert not (imported & FORBIDDEN_RUNNER), imported & FORBIDDEN_RUNNER


def test_runner_hitl_goes_through_public_endpoints():
    """Approvals/clarifications via HTTP paths, never service imports."""
    source = (EVAL_DIR / "runner.py").read_text(encoding="utf-8")
    imported = _imports_of(EVAL_DIR / "runner.py")
    assert "agent.services" not in source
    assert "approval_service" not in imported and "clarification_service" not in imported
    assert "/api/approvals" in source
    assert "/api/clarifications" in source
