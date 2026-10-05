"""Phase 29 secret scan: fail on secrets in tracked files.

Patterns cover private keys, cloud/API key formats, and assigned
credential values. References are fine (getenv, placeholders, docs
naming a variable); VALUES are not. An allowlist pins the known-safe
hits (test secrets, docs examples) so new ones fail loudly. Run with
`python scripts/secret_scan.py` (also a `make secret-scan` target).
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PATTERNS = {
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "aws-key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "github-token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    "openai-key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    "slack-token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    "assigned-api-key": re.compile(
        r"(?i)\b(?:INCEPTION_API_KEY|API_KEY|API_SECRET|SECRET_KEY)\b\s*[:=]\s*"
        r"(?!['\"]?(?:test|example|placeholder|changeme|xxx|your-|none))"
        r"(?![A-Za-z_][A-Za-z0-9_]*\s*[,)])"  # kwarg pass-through, not a value
        r"['\"]?[^\s'\"]{8,}"
    ),
    "bearer-literal": re.compile(r"(?i)\bbearer\s+[A-Za-z0-9\-._~+/]{20,}={0,2}\b"),
}

# (relative path, pattern name, reason): reviewed, safe to keep.
ALLOWLIST = {
    ("tests/policy/test_policy_service.py", "bearer-literal", "local-operator-token fixture"),
    ("tests/integration/test_evaluation_api.py", "bearer-literal", "local-operator-token fixture"),
    ("docs/evaluation.md", "bearer-literal", "local-operator-token docs example"),
    ("docs/how-to-run.md", "bearer-literal", "local-operator-token docs example"),
    ("frontend/e2e/ops-faults.spec.ts", "bearer-literal", "local-operator-token e2e fixture"),
}

SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2", ".ttf"}
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv"}


def tracked_files() -> list[Path]:
    """Git-tracked files (the scan covers what ships, not local .env)."""
    out = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    )
    return [ROOT / part for part in out.stdout.decode().split("\0") if part]


def scan() -> list[str]:
    """Pattern hits outside the allowlist, as `path:line:name` strings."""
    hits = []
    for path in tracked_files():
        if path.suffix.lower() in SKIP_SUFFIXES:
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="strict").splitlines()
        except (UnicodeDecodeError, OSError):
            continue
        rel = path.relative_to(ROOT).as_posix()
        for number, line in enumerate(lines, 1):
            if ".get(" in line or "getenv" in line or "environ" in line:
                continue  # reads (source.get("INCEPTION_API_KEY")) are not values
            for name, pattern in PATTERNS.items():
                if pattern.search(line) and (rel, name, "") not in {
                    (a, b, "") for a, b, _ in ALLOWLIST
                }:
                    if (rel, name, _allow_reason(rel, name)) in ALLOWLIST:
                        continue
                    hits.append(f"{rel}:{number}:{name}")
    return hits


def _allow_reason(rel: str, name: str) -> str:
    for allowed_rel, allowed_name, reason in ALLOWLIST:
        if (allowed_rel, allowed_name) == (rel, name):
            return reason
    return ""


def main() -> int:
    """Exit 1 with the hit list when unreviewed secrets are present."""
    hits = scan()
    if hits:
        print("secret scan FAILED — unreviewed hits:")
        for hit in hits:
            print(f"  {hit}")
        print("Add a reviewed entry to ALLOWLIST or remove the secret.")
        return 1
    print(f"secret scan passed ({len(tracked_files())} tracked files).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
