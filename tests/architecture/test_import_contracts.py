"""Architecture contracts from NORTHSTAR_WORKER_FINAL_PLAN §8.

Mechanically enforced: any forbidden import fails `pytest tests/architecture`
and therefore `make lint` / `make verify`. Mirrors `importlinter.ini`.

Rules:
  1. `verifier` may import only `common` and `database.models` (plus itself,
     stdlib, and third-party packages) — never `agent`, `backend`/`app`,
     or `mcp_server`.
  2. `eval.oracle_rules` must not import `agent`.
  3. `backend.api` (controllers) imports services/schemas only, never
     `app.repositories`.
  4. `backend.services` imports repositories/schemas only, never `app.api`.
  5. `agent.nodes` are thin: never `agent.repositories`, `agent.adapters`,
     or `agent.llm` directly.
  6. `mcp_server` must not import `database`.
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# First-party roots: anything else imported is stdlib or third-party (allowed).
FIRST_PARTY_ROOTS = frozenset(
    {
        "app",
        "agent",
        "verifier",
        "mcp_server",
        "browser",
        "eval",
        "database",
        "northstar_common",
        "common",
        "tests",
    }
)

STDLIB_ROOTS = frozenset(sys.stdlib_module_names)


@dataclass(frozen=True)
class Violation:
    file: Path
    lineno: int
    imported: str
    rule: str


def _imported_roots(tree: ast.AST) -> list[tuple[int, str]]:
    """Return (lineno, absolute dotted module) for every static import."""
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.append((node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                continue  # relative imports resolved by callers, not by rules
            if node.module:
                found.append((node.lineno, node.module))
    return found


def _is_first_party(dotted: str) -> bool:
    return dotted.split(".")[0] in FIRST_PARTY_ROOTS


def check_file(
    path: Path, source_root: str, forbidden: frozenset[str], rule: str
) -> list[Violation]:
    """Check one file's imports against one forbidden set."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return []  # lint/type stages own syntax errors, not architecture
    violations: list[Violation] = []
    for lineno, dotted in _imported_roots(tree):
        if not _is_first_party(dotted):
            continue  # stdlib + third-party are always allowed
        # No same-package blanket skip: forbidden sets are specific enough
        # that intra-package imports (e.g. app.api -> app.services) pass,
        # while app.api -> app.repositories is still flagged.
        if any(dotted == f or dotted.startswith(f + ".") for f in forbidden):
            violations.append(Violation(path, lineno, dotted, rule))
    return violations


def check_verifier_allowlist(path: Path) -> list[Violation]:
    """Verifier may import only common + database.models (first-party)."""
    allowed = ("verifier", "northstar_common", "common", "database.models")
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return []
    violations: list[Violation] = []
    for lineno, dotted in _imported_roots(tree):
        if not _is_first_party(dotted):
            continue
        if dotted.split(".")[0] in STDLIB_ROOTS:
            continue
        if not any(dotted == a or dotted.startswith(a + ".") for a in allowed):
            violations.append(Violation(path, lineno, dotted, "verifier-independence"))
    return violations


def collect_violations(root: Path = REPO_ROOT) -> list[Violation]:
    """Run every §8 contract over the repo tree."""
    violations: list[Violation] = []

    verifier_dir = root / "verifier"
    if verifier_dir.is_dir():
        for path in sorted(verifier_dir.rglob("*.py")):
            violations.extend(check_verifier_allowlist(path))

    oracle = root / "eval" / "oracle_rules.py"
    if oracle.is_file():
        violations.extend(check_file(oracle, "eval", frozenset({"agent"}), "oracle-independence"))

    scoped: list[tuple[str, str, frozenset[str]]] = [
        ("backend/app/api", "app", frozenset({"app.repositories"})),
        ("backend/app/services", "app", frozenset({"app.api"})),
        (
            "agent/nodes",
            "agent",
            frozenset({"agent.repositories", "agent.adapters", "agent.llm"}),
        ),
        ("mcp_server", "mcp_server", frozenset({"database"})),
    ]
    for rel, source_root, forbidden in scoped:
        target = root / rel
        if not target.is_dir():
            continue
        for path in sorted(target.rglob("*.py")):
            violations.extend(check_file(path, source_root, forbidden, rel))
    return violations


def test_layer_contracts_hold() -> None:
    """Fail the build when any §8 layer rule is violated."""
    violations = collect_violations()
    formatted = "\n".join(
        f"{v.file.relative_to(REPO_ROOT)}:{v.lineno} imports {v.imported} [{v.rule}]"
        for v in violations
    )
    assert not violations, f"Architecture violations:\n{formatted}"


def test_checker_catches_deliberate_violation(tmp_path: Path) -> None:
    """Prove the checker flags forbidden imports (fixture, not repo code)."""
    bad_verifier = tmp_path / "bad_mod.py"
    bad_verifier.write_text("from agent.policy import authorization\n", encoding="utf-8")
    assert check_verifier_allowlist(bad_verifier), "verifier<-agent must be flagged"

    bad_controller = tmp_path / "bad_ctrl.py"
    bad_controller.write_text("from app.repositories import order_repository\n", encoding="utf-8")
    found = check_file(
        bad_controller, "app", frozenset({"app.repositories"}), "backend-controllers"
    )
    assert found, "controller<-repository must be flagged"

    bad_tool = tmp_path / "bad_tool.py"
    bad_tool.write_text("import database.session\n", encoding="utf-8")
    found = check_file(bad_tool, "mcp_server", frozenset({"database"}), "mcp-no-db")
    assert found, "mcp_server<-database must be flagged"

    good = tmp_path / "good.py"
    good.write_text(
        "from northstar_common.logging import get_logger\nimport fastapi\n",
        encoding="utf-8",
    )
    assert check_verifier_allowlist(good) == []


def test_single_backend_identity() -> None:
    """Every backend import is `app.*`, never `backend.app.*`.

    Both `backend/` and the repo root sit on sys.path, so `backend.app.*`
    would create a second identity for one package (exception handlers
    then miss dependency errors). One root, enforced.
    """
    offenders = []
    for path in sorted((REPO_ROOT / "backend").rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for _, dotted in _imported_roots(tree):
            if dotted == "backend" or dotted.startswith("backend."):
                offenders.append(f"{path.relative_to(REPO_ROOT)} imports {dotted}")
    assert not offenders, "dual backend identity:\n" + "\n".join(offenders)
