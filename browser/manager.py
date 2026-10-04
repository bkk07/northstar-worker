"""Session manager: one browser session per run id.

Headless in eval, headed with `slow_mo` in demo mode. Storage state is
keyed by run id, so a runner restart resumes the same `/ops` session.
"""

from browser.session import BrowserSession


class SessionManager:
    """Owns the live sessions (close_all on runner shutdown)."""

    def __init__(
        self,
        frontend_origin: str = "http://localhost:5173",
        storage_dir: str = "storage",
        screenshot_dir: str = "screenshots",
    ) -> None:
        self.frontend_origin = frontend_origin
        self.storage_dir = storage_dir
        self.screenshot_dir = screenshot_dir
        self._sessions: dict[str, BrowserSession] = {}

    def open(self, run_id: str, headless: bool = True, slow_mo: int = 0) -> BrowserSession:
        """Open (or replace) the session for a run."""
        self.close(run_id)
        session = BrowserSession(
            run_id,
            frontend_origin=self.frontend_origin,
            headless=headless,
            slow_mo=slow_mo,
            storage_dir=self.storage_dir,
            screenshot_dir=self.screenshot_dir,
        ).start()
        self._sessions[run_id] = session
        return session

    def get(self, run_id: str) -> BrowserSession:
        """Live session for a run (KeyError when absent)."""
        return self._sessions[run_id]

    def close(self, run_id: str) -> None:
        """Stop and forget one run's session (idempotent)."""
        session = self._sessions.pop(run_id, None)
        if session is not None:
            session.stop()

    def close_all(self) -> None:
        """Stop every live session."""
        for run_id in list(self._sessions):
            self.close(run_id)
