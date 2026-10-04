"""Accessibility perception: snapshot the page into ephemeral refs.

`observe(page)` returns an Observation: the URL, title, a `page_version`
hash over the interactive structure, and a ref table binding `e1…eN` to
locator strategies. Refs die on the next observation; actions carrying an
older `page_version` raise StaleReference (fail fast, then re-observe).
"""

import hashlib
from dataclasses import dataclass, field

from browser.locators import RefTarget

SNAPSHOT_JS = """() => {
  const pick = (el) => {
    if (el.getAttribute("aria-label")) return el.getAttribute("aria-label").trim();
    const labelledBy = el.getAttribute("aria-labelledby");
    if (labelledBy) {
      const text = labelledBy.split(/\\s+/)
        .map((id) => document.getElementById(id))
        .filter(Boolean)
        .map((n) => n.innerText || n.textContent || "")
        .join(" ").trim();
      if (text) return text;
    }
    if (el.labels && el.labels.length) {
      const text = Array.from(el.labels).map((l) => l.innerText || "").join(" ").trim();
      if (text) return text;
    }
    return "";
  };
  const implicitRole = (el) => {
    const tag = el.tagName.toLowerCase();
    if (tag === "button") return "button";
    if (tag === "a" && el.hasAttribute("href")) return "link";
    if (tag === "select") return "combobox";
    if (tag === "textarea") return "textbox";
    if (tag === "input") {
      const type = (el.getAttribute("type") || "text").toLowerCase();
      if (["checkbox", "radio", "button", "submit", "search"].includes(type))
        return type === "search" ? "searchbox" : type;
      return "textbox";
    }
    return "";
  };
  const out = [];
  const seen = new Set();
  const nodes = document.querySelectorAll(
    "a[href], button, input, select, textarea, [role=button], [role=link], " +
    "[role=textbox], [role=checkbox], [role=radio], [role=combobox], [role=searchbox]"
  );
  nodes.forEach((el) => {
    if (seen.has(el)) return;
    seen.add(el);
    const rect = el.getBoundingClientRect();
    const formHost = el.closest("form[aria-label]");
    const form = formHost ? (formHost.getAttribute("aria-label") || "") : "";
    const role = el.getAttribute("role") || implicitRole(el);
    const name = pick(el) || (el.innerText || el.textContent || "").trim().slice(0, 80)
      || el.getAttribute("placeholder") || el.getAttribute("title") || el.getAttribute("alt") || "";
    out.push({
      tag: el.tagName.toLowerCase(),
      role,
      name,
      form,
      type: el.getAttribute("type") || "",
      value: el.value !== undefined ? String(el.value).slice(0, 120) : "",
      disabled: !!el.disabled,
      checked: !!el.checked,
      href: el.getAttribute("href") || "",
      visible: rect.width > 0 && rect.height > 0,
    });
  });
  return out;
}"""


@dataclass(frozen=True)
class Observation:
    """One perception frame: identity, version, and the ref table."""

    url: str
    title: str
    page_version: str
    refs: dict[str, RefTarget] = field(default_factory=dict)

    def find(self, role: str = "", name: str = "", form: str = "") -> list[RefTarget]:
        """Refs matching role, name substring, and enclosing form (discovery)."""
        want_role = role.lower()
        want_name = name.lower()
        want_form = form.lower()
        return [
            target
            for target in self.refs.values()
            if (not want_role or target.role.lower() == want_role)
            and (not want_name or want_name in (target.name or "").lower())
            and (not want_form or want_form in (target.extra.get("form") or "").lower())
        ]


def compute_version(url: str, elements: list[dict]) -> str:
    """Hash of the interactive structure (order- and label-sensitive)."""
    signature = "|".join(f"{el.get('tag')}:{el.get('role')}:{el.get('name')}" for el in elements)
    return hashlib.sha256(f"{url}#{signature}".encode()).hexdigest()[:16]


def observe(page, settle_timeout_ms: int = 4000) -> Observation:
    """Snapshot the page into an Observation with fresh ephemeral refs.

    Waits for the DOM to settle first (two identical frames): lazy chunks
    and loaders finish before refs bind, so actions never target a
    half-rendered tree.
    """
    elements = _snapshot_settled(page, settle_timeout_ms)
    refs: dict[str, RefTarget] = {}
    for index, el in enumerate(elements, start=1):
        ref = f"e{index}"
        role, name = el.get("role", ""), el.get("name", "")
        if el.get("tag") in ("input", "select", "textarea") and name:
            refs[ref] = RefTarget(
                ref=ref,
                kind="label",
                role=role or el.get("tag", ""),
                name=name,
                value=name,
                extra=el,
            )
        elif role and name:
            refs[ref] = RefTarget(ref=ref, kind="role", role=role, name=name, extra=el)
        elif name:
            refs[ref] = RefTarget(ref=ref, kind="text", value=name, extra=el)
        else:
            refs[ref] = RefTarget(ref=ref, kind="text", value=el.get("tag", ""), extra=el)
    url = page.url
    return Observation(
        url=url,
        title=page.title(),
        page_version=compute_version(url, elements),
        refs=refs,
    )


def _snapshot_settled(page, settle_timeout_ms: int) -> list[dict]:
    """Poll the snapshot until two consecutive frames agree (or timeout)."""
    import time

    deadline = time.monotonic() + settle_timeout_ms / 1000
    previous: list[dict] | None = None
    current: list[dict] = page.evaluate(SNAPSHOT_JS)
    while time.monotonic() < deadline:
        if previous == current:
            return current
        previous = current
        page.wait_for_timeout(300)
        current = page.evaluate(SNAPSHOT_JS)
    return current


def dump_text(observation: Observation) -> str:
    """Compact human rendering (logs, timeline, debugging)."""
    lines = [f"url={observation.url} version={observation.page_version}"]
    for ref, target in observation.refs.items():
        lines.append(f"[{ref}] {target.role or target.kind} {target.name or target.value!r}")
    return "\n".join(lines)
