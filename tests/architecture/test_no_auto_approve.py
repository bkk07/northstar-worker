"""No auto-approve code path (Phase 22).

An approval reaches `approved` through exactly one write site: the
operator endpoint service. The agent only consumes (`approved` to
`consumed`); nothing anywhere invents an approval. Reads of the status
are unrestricted — only writes are pinned.
"""

import ast
from pathlib import Path, PurePath

REPO_ROOT = Path(__file__).resolve().parents[2]

SCANNED_ROOTS = (
    "agent",
    "backend",
    "browser",
    "common",
    "database",
    "eval",
    "mcp_server",
    "verifier",
)

# The single sanctioned write site (operator decision endpoint).
SANCTIONED = {"backend/app/services/worker/approval_service.py"}


def _approved_writes(path: Path) -> list[str]:
    """Locations in one file that write status `approved`."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets = [t.attr for t in node.targets if isinstance(t, ast.Attribute)]
            if "status" in targets and isinstance(node.value, ast.Constant):
                if node.value.value == "approved":
                    hits.append(f"{path.relative_to(REPO_ROOT)}:{node.lineno}")
        for keyword in getattr(node, "keywords", []):
            if keyword.arg == "status" and isinstance(keyword.value, ast.Constant):
                if keyword.value.value == "approved":
                    hits.append(f"{path.relative_to(REPO_ROOT)}:{node.lineno}")
    return hits


def test_approved_written_only_by_operator_endpoint():
    """Fail when any other module writes the approved status."""
    offenders = []
    for root in SCANNED_ROOTS:
        for path in sorted((REPO_ROOT / root).rglob("*.py")):
            for hit in _approved_writes(path):
                if PurePath(hit.rsplit(":", 1)[0]).as_posix() not in SANCTIONED:
                    offenders.append(hit)
    assert not offenders, "unsanctioned approved writes:\n" + "\n".join(offenders)
