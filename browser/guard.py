"""Top-level navigation allowlist: the worker's browser lives on the
commerce surfaces only (`/ops/*`, `/shop/*`). `/worker`, `/evaluation`
and `/api/control/*` are unreachable by construction (plan §5, §15).

XHRs/fetch from the page (`/api/ops/*`, `/api/read/*`) are allowed because
the page needs them; only top-level navigations are gated.
"""

from urllib.parse import urlparse

ALLOWED_PREFIXES = ("/ops", "/shop")


def is_navigation_allowed(url: str, origin: str) -> bool:
    """True when a top-level navigation to `url` stays inside the sandbox."""
    try:
        current = urlparse(url)
        base = urlparse(origin)
    except ValueError:
        return False
    if current.scheme not in ("http", "https"):
        return False
    if (current.scheme, current.hostname, current.port) != (
        base.scheme,
        base.hostname,
        base.port,
    ):
        return False
    path = current.path or "/"
    return path == "/ops" or path == "/shop" or path.startswith(("/ops/", "/shop/"))


def install_route_guard(page, origin: str) -> None:
    """Abort disallowed top-level navigations; let page traffic through."""

    def handle(route) -> None:
        request = route.request
        if request.is_navigation_request():
            if is_navigation_allowed(request.url, origin):
                route.continue_()
            else:
                route.abort()
        else:
            route.continue_()

    page.route("**/*", handle)
