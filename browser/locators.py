"""Ref → locator strategies. Refs are ephemeral handles minted by the
observer; resolution uses accessibility queries only (role + name, label,
text). No CSS/XPath selectors anywhere in this layer.
"""

from dataclasses import dataclass, field
from typing import Literal

from browser.errors import ElementNotFound

RefKind = Literal["role", "label", "text"]


@dataclass(frozen=True)
class RefTarget:
    """One bound ref: how to find the element again."""

    ref: str
    kind: RefKind
    role: str = ""
    name: str = ""
    value: str = ""
    extra: dict = field(default_factory=dict)


def resolve(page, target: RefTarget):
    """Resolve a ref to a locator with exactly one match, else raise.

    Refs discovered inside a labeled form (or dialog) resolve within that
    scope, so identically labeled fields in sibling forms stay unambiguous.
    """
    form_name = (target.extra or {}).get("form") or ""
    form_role = (target.extra or {}).get("form_role") or "form"
    scope = page.get_by_role(form_role, name=form_name) if form_name else page
    if target.kind == "role":
        locator = scope.get_by_role(target.role, name=target.name)
    elif target.kind == "label":
        locator = scope.get_by_label(target.value)
    else:
        locator = scope.get_by_text(target.value)
    try:
        count = locator.count()
    except Exception as exc:
        raise ElementNotFound(f"ref {target.ref} could not be resolved: {exc}") from exc
    if count != 1:
        raise ElementNotFound(f"ref {target.ref} resolved to {count} elements, want 1")
    return locator
