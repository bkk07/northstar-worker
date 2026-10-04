"""Browser tools: session lifecycle, navigation, observation.

Public functions are async (the MCP server awaits them); all Playwright
work hops to the dedicated browser thread (see browser_thread).
"""

from mcp_server import context
from mcp_server.browser_thread import run_browser
from mcp_server.schemas.tools import (
    BrowserBackInput,
    BrowserNavigateInput,
    BrowserObserveInput,
    BrowserOpenInput,
    BrowserScreenshotInput,
)


def _observe_dict(task_id: str, session) -> dict:
    """Serve a fresh observation and record its version baseline."""
    observation = session.observe()
    context.set_served_version(task_id, observation.page_version)
    return {
        "url": observation.url,
        "title": observation.title,
        "page_version": observation.page_version,
        "refs": {
            ref: {
                "kind": target.kind,
                "role": target.role,
                "name": target.name,
                "value": target.value,
                "form": (target.extra or {}).get("form", ""),
                "form_role": (target.extra or {}).get("form_role", ""),
            }
            for ref, target in observation.refs.items()
        },
    }


def _fresh_or_stale(task_id: str, session):
    """Re-observe and fail when the page moved since the served version."""
    from browser.errors import StaleReference

    fresh = session.observe()
    served = context.served_version(task_id)
    if served is not None and fresh.page_version != served:
        context.set_served_version(task_id, fresh.page_version)
        raise StaleReference("page moved since the last observation — observe explicitly, then act")
    return fresh


def _open_impl(task_id: str, target: str, headless: bool) -> dict:
    args = BrowserOpenInput(task_id=task_id, target=target, headless=headless)
    context.store().check(args.task_id, "browser")
    manager = context.browser_manager()
    try:
        session = manager.get(args.task_id)
        live = session.started
    except KeyError:
        live = False
    if not live:
        session = manager.open(args.task_id, headless=args.headless)
    session.navigate(f"/{args.target}")
    return _observe_dict(args.task_id, session)


async def browser_open(task_id: str, target: str = "ops", headless: bool = True) -> dict:
    """Open (or reuse) the task's session on a commerce surface."""
    return await run_browser(_open_impl, task_id, target, headless)


def _navigate_impl(task_id: str, route: str) -> dict:
    args = BrowserNavigateInput(task_id=task_id, route=route)
    context.store().check(args.task_id, "browser")
    session = context.browser_manager().get(args.task_id)
    session.navigate(args.route)
    return _observe_dict(args.task_id, session)


async def browser_navigate(task_id: str, route: str) -> dict:
    """Navigate inside the URL guard (violations are errors, never bypasses)."""
    return await run_browser(_navigate_impl, task_id, route)


def _observe_impl(task_id: str) -> dict:
    args = BrowserObserveInput(task_id=task_id)
    context.store().check(args.task_id, "browser")
    session = context.browser_manager().get(args.task_id)
    return _observe_dict(args.task_id, session)


async def browser_observe(task_id: str) -> dict:
    """Fresh observation (rebinds refs, re-baselines staleness)."""
    return await run_browser(_observe_impl, task_id)


def _back_impl(task_id: str) -> dict:
    args = BrowserBackInput(task_id=task_id)
    context.store().check(args.task_id, "browser")
    session = context.browser_manager().get(args.task_id)
    session._page.go_back()
    return _observe_dict(args.task_id, session)


async def browser_back(task_id: str) -> dict:
    """Browser back navigation, then a fresh observation."""
    return await run_browser(_back_impl, task_id)


def _screenshot_impl(task_id: str, label: str) -> dict:
    args = BrowserScreenshotInput(task_id=task_id, label=label)
    context.store().check(args.task_id, "browser")
    session = context.browser_manager().get(args.task_id)
    return {"path": session.screenshot(args.label)}


async def browser_screenshot(task_id: str, label: str) -> dict:
    """Labeled screenshot into the run's evidence trail."""
    return await run_browser(_screenshot_impl, task_id, label)
