"""Mutation-request capture: every `/api/ops/*` POST with its HTTP status.

After `browser_submit`, the observation carries the status, so the agent
reasons about the commit from captured traffic — never from toasts alone.
"""

from dataclasses import dataclass, field


@dataclass
class MutationCall:
    """One captured ops mutation request."""

    method: str
    url: str
    status: int
    body: str = ""


@dataclass
class NetworkCapture:
    """Response listener scoped to ops mutation traffic."""

    calls: list[MutationCall] = field(default_factory=list)

    def attach(self, page) -> None:
        """Start recording `/api/ops/*` responses on a page."""
        page.on("response", self._handle)

    def detach(self, page) -> None:
        """Stop recording on a page."""
        try:
            page.remove_listener("response", self._handle)
        except Exception:
            pass

    def _handle(self, response) -> None:
        url = response.url
        if "/api/ops/" not in url:
            return
        try:
            status = response.status
        except Exception:
            return
        try:
            body = response.text()[:2000]
        except Exception:
            body = ""
        try:
            method = response.request.method
        except Exception:
            method = ""
        self.calls.append(MutationCall(method=method, url=url, status=status, body=body))

    def last_mutation(self, method: str = "POST") -> MutationCall | None:
        """Most recent captured mutation call (any URL), if any."""
        for call in reversed(self.calls):
            if call.method == method:
                return call
        return None

    def last_status(self, url_part: str) -> int | None:
        """Most recent status for calls whose URL contains `url_part`."""
        for call in reversed(self.calls):
            if url_part in call.url:
                return call.status
        return None

    def clear(self) -> None:
        """Forget captured calls (fresh step)."""
        self.calls.clear()
