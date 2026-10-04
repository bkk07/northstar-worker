"""Screenshots at significant steps (timeline evidence, debugging)."""

import re
from pathlib import Path


def capture(page, label: str, run_dir: str | Path) -> str:
    """Save a PNG screenshot; return the file path as a string."""
    directory = Path(run_dir)
    directory.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", label).strip("_") or "shot"
    path = directory / f"{safe}.png"
    page.screenshot(path=str(path))
    return str(path)
