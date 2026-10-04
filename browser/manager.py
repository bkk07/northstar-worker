"""Session manager: one browser session per run id.

One shared Chromium per manager (Playwright's sync API supports a single
live instance per thread): sessions are isolated contexts with per-run
storage state. Headless in eval, headed with `slow_mo` in demo mode —
the first open wins the launch flags for the process lifetime.
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
        self._playwright = None
        self._browser = None
        self._browser_headless: bool | None = None

    def _ensure_browser(self, headless: bool):
        """Launch the shared browser once (relaunch on headless change)."""
        if self._browser is None or self._browser_headless != headless:
            self.close_all()
            from playwright.sync_api import sync_playwright

            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=headless)
            self._browser_headless = headless

    def open(self, run_id: str, headless: bool = True, slow_mo: int = 0) -> BrowserSession:
        """Open (or replace) the session for a run on the shared browser."""
        self.close(run_id)
        self._ensure_browser(headless)
        session = BrowserSession(
            run_id,
            frontend_origin=self.frontend_origin,
            headless=headless,
            slow_mo=slow_mo,
            storage_dir=self.storage_dir,
            screenshot_dir=self.screenshot_dir,
            _shared=(self._playwright, self._browser),
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
        """Stop every session, then the shared browser."""
        for run_id in list(self._sessions):
            self.close(run_id)
        if self._browser is not None:
            self._browser.close()
            self._browser = None
        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None
        self._browser_headless = None
