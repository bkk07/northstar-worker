"""Prompt loader: system prompts for each proposal type.

Prompts live as Markdown next to this module so operators can read them
without parsing Python. Memory facts are injected by the caller as a
bounded structured block (Phase 23); customer-controlled text always
arrives wrapped as `<untrusted_data>` and never as instructions.
"""

from pathlib import Path

_PROMPT_DIR = Path(__file__).parent


def get_prompt(name: str) -> str:
    """Load a system prompt by base name (`understand`, `plan`, ...)."""
    path = _PROMPT_DIR / f"{name}.md"
    if not path.is_file():
        raise FileNotFoundError(f"unknown prompt: {name}")
    return path.read_text(encoding="utf-8").strip()
