"""Browser session: one Chromium context per run with perception + guard.

- Storage state persists per run, so sessions survive a runner restart.
- The route guard aborts top-level navigations outside `/ops`, `/shop`.
- Actions resolve ephemeral refs (role/label/text only, never selectors),
  enforce the caller's `page_version` (stale → StaleReference), and apply
  per-action timeouts.
- Network capture records every `/api/ops/*` mutation with its status.
"""

from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from browser import guard as route_guard
from browser import screenshots
from browser.errors import (
    ActionTimeout,
    BrowserError,
    ElementNotFound,
    GuardViolation,
    StaleReference,
)
from browser.locators import resolve
from browser.network_capture import NetworkCapture
from browser.observer import Observation, observe


class BrowserSession:
    """One headed/headless Chromium session bound to a run id."""

    def __init__(
        self,
        run_id: str,
        frontend_origin: str = "http://localhost:5173",
        headless: bool = True,
        slow_mo: int = 0,
        storage_dir: str | Path = "storage",
        screenshot_dir: str | Path = "screenshots",
        action_timeout_ms: int = 10_000,
        navigation_timeout_ms: int = 15_000,
    ) -> None:
        self.run_id = run_id
        self.frontend_origin = frontend_origin.rstrip("/")
        self.headless = headless
        self.slow_mo = slow_mo
        self.storage_path = Path(storage_dir) / f"{run_id}.json"
        self.screenshot_dir = Path(screenshot_dir) / run_id
        self.action_timeout_ms = action_timeout_ms
        self.navigation_timeout_ms = navigation_timeout_ms
        self.network = NetworkCapture()
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._refs: dict = {}
        self._version: str | None = None

    # -- lifecycle ------------------------------------------------------

    def start(self):
        """Launch Chromium, restore storage, install guard + capture."""
        from playwright.sync_api import sync_playwright

        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=self.headless, slow_mo=self.slow_mo
        )
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        kwargs = {}
        if self.storage_path.exists():
            kwargs["storage_state"] = str(self.storage_path)
        self._context = self._browser.new_context(**kwargs)
        self._context.set_default_timeout(self.action_timeout_ms)
        self._page = self._context.new_page()
        self._page.on("popup", lambda popup: popup.close())
        route_guard.install_route_guard(self._page, self.frontend_origin)
        self.network.attach(self._page)
        return self

    def stop(self) -> None:
        """Detach listeners and close everything (keeps the storage file)."""
        try:
            if self._page is not None:
                self.network.detach(self._page)
        finally:
            self._page = None
        if self._context is not None:
            self._context.close()
            self._context = None
        if self._browser is not None:
            self._browser.close()
            self._browser = None
        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None
        self._refs = {}
        self._version = None

    def save_storage_state(self) -> str:
        """Persist cookies/session; returns the storage file path."""
        if self._context is None:
            raise BrowserError("session is not started")
        self._context.storage_state(path=str(self.storage_path))
        return str(self.storage_path)

    @property
    def started(self) -> bool:
        """True while the page is live."""
        return self._page is not None

    # -- navigation / perception ----------------------------------------

    def navigate(self, path: str):
        """Top-level navigation inside the allowlist (else GuardViolation)."""
        self._require_started()
        url = path if "://" in path else f"{self.frontend_origin}{path}"
        if not route_guard.is_navigation_allowed(url, self.frontend_origin):
            raise GuardViolation(f"navigation blocked by URL guard: {url}")
        try:
            self._page.goto(url, timeout=self.navigation_timeout_ms)
        except PlaywrightTimeoutError as exc:
            raise ActionTimeout(f"navigation to {url} timed out") from exc
        return self.observe()

    def observe(self) -> Observation:
        """Snapshot the page; rebinds refs and the page version."""
        self._require_started()
        observation = observe(self._page)
        self._refs = dict(observation.refs)
        self._version = observation.page_version
        return observation

    # -- actions ----------------------------------------------------------

    def click(self, ref: str, expected_version: str | None = None, timeout_ms: int | None = None):
        """Click a ref (stale version or detached element → StaleReference)."""
        locator = self._resolve(ref, expected_version)
        try:
            locator.click(timeout=timeout_ms or self.action_timeout_ms)
        except PlaywrightTimeoutError as exc:
            raise ActionTimeout(f"click {ref} timed out") from exc
        except PlaywrightError as exc:
            raise self._classify_action_error(ref, exc) from exc

    def fill(
        self,
        ref: str,
        value: str,
        expected_version: str | None = None,
        timeout_ms: int | None = None,
    ):
        """Fill a ref (stale version or detached element → StaleReference)."""
        locator = self._resolve(ref, expected_version)
        try:
            locator.fill(value, timeout=timeout_ms or self.action_timeout_ms)
        except PlaywrightTimeoutError as exc:
            raise ActionTimeout(f"fill {ref} timed out") from exc
        except PlaywrightError as exc:
            raise self._classify_action_error(ref, exc) from exc

    def screenshot(self, label: str) -> str:
        """Capture a labeled screenshot for the run's evidence trail."""
        self._require_started()
        return screenshots.capture(self._page, label, self.screenshot_dir)

    # -- internals ----------------------------------------------------------

    def _require_started(self) -> None:
        if self._page is None:
            raise BrowserError("session is not started")

    def _check_version(self, expected_version: str | None) -> None:
        if expected_version is not None and expected_version != self._version:
            raise StaleReference(
                f"page moved on (have {self._version}, action carries {expected_version})"
            )

    def _resolve(self, ref: str, expected_version: str | None):
        self._require_started()
        self._check_version(expected_version)
        target = self._refs.get(ref)
        if target is None:
            raise ElementNotFound(f"unknown ref {ref} — re-observe first")
        return resolve(self._page, target)

    @staticmethod
    def _classify_action_error(ref: str, exc: PlaywrightError) -> BrowserError:
        message = str(exc).lower()
        if "not attached" in message or "detached" in message or "stale" in message:
            return StaleReference(f"ref {ref} went stale: {exc}")
        if "timeout" in message:
            return ActionTimeout(f"action {ref} timed out: {exc}")
        return BrowserError(f"action {ref} failed: {exc}")


def storage_path_for(storage_dir: str | Path, run_id: str) -> str:
    """Storage-state file for a run (stable across restarts)."""
    return str(Path(storage_dir) / f"{run_id}.json")
