"""Browser-layer errors (mapped to FailureType by the classifier in Phase 17)."""


class BrowserError(Exception):
    """Base browser failure."""

    code = "BROWSER_ERROR"


class GuardViolation(BrowserError):
    """Top-level navigation outside /ops and /shop was blocked."""

    code = "GUARD_VIOLATION"


class ElementNotFound(BrowserError):
    """A ref resolved to zero (or ambiguous) elements."""

    code = "ELEMENT_NOT_FOUND"


class StaleReference(BrowserError):
    """A ref from an older page version, or a detached element."""

    code = "STALE_REF"


class ActionTimeout(BrowserError):
    """An action exceeded its per-action deadline."""

    code = "TIMEOUT"
