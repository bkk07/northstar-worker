"""No task names in agent logic: generalization guard (plan §28, Test J).

New workflows arrive via the effect registry — never via task-name
branches in graph, node, failure, tool, or browser code. This test scans
every `agent/**/*.py` file for catalog codes and scenario proper nouns.
(Prompt files under `agent/llm/prompts/` deliberately show code *formats*
like `C102` so the model learns them; they are data, not branches, and
are covered by review rather than this scan.)
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

CODE_PATTERNS = (
    re.compile(r"\bORD-\d+"),
    re.compile(r"\bTCK-[A-Z0-9-]+"),
    re.compile(r"\bC10\d\b"),
)

TASK_WORDS = (
    "ProBook",
    "Nova Phone",
    "QLED",
    "pepperoni",
    "pizza",
    "Priya",
    "Nair",
    "Nayar",
    "headphones",
    "mixer",
    "flickering",
    "shattered",
    "dented",
    "Headphones",
)


def test_no_task_names_in_agent_code():
    """Fail when scenario vocabulary leaks into agent logic."""
    offenders = []
    for path in sorted((REPO_ROOT / "agent").rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for pattern in CODE_PATTERNS:
            if pattern.search(text):
                offenders.append(f"{path.relative_to(REPO_ROOT)}: code {pattern.pattern}")
        for word in TASK_WORDS:
            if re.search(rf"\b{re.escape(word)}\b", text):
                offenders.append(f"{path.relative_to(REPO_ROOT)}: word {word!r}")
    assert not offenders, "task names in agent logic:\n" + "\n".join(offenders)
