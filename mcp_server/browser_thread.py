"""Dedicated single thread for sync Playwright work.

The MCP server runs on asyncio, and Playwright's sync API refuses to run
inside a running event loop. Every browser call hops to this thread, so all
Playwright objects live on one loop-free thread.
"""

import asyncio
import functools
from concurrent.futures import ThreadPoolExecutor

_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="browser")

# Backstop behind Playwright's own per-action timeouts: a hung call fails
# the tool (recovery routes it) instead of wedging the server forever.
BROWSER_CALL_TIMEOUT_S = 90.0


async def run_browser(func, *args, **kwargs):
    """Run a blocking browser callable on the browser thread."""
    loop = asyncio.get_running_loop()
    try:
        return await asyncio.wait_for(
            loop.run_in_executor(_EXECUTOR, functools.partial(func, *args, **kwargs)),
            timeout=BROWSER_CALL_TIMEOUT_S,
        )
    except TimeoutError as exc:
        raise RuntimeError(
            f"browser call {getattr(func, '__name__', 'unknown')} timed out "
            f"after {BROWSER_CALL_TIMEOUT_S}s"
        ) from exc
