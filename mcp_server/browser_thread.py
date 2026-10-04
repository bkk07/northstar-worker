"""Dedicated single thread for sync Playwright work.

The MCP server runs on asyncio, and Playwright's sync API refuses to run
inside a running event loop. Every browser call hops to this thread, so all
Playwright objects live on one loop-free thread.
"""

import asyncio
import functools
from concurrent.futures import ThreadPoolExecutor

_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="browser")


async def run_browser(func, *args, **kwargs):
    """Run a blocking browser callable on the browser thread."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_EXECUTOR, functools.partial(func, *args, **kwargs))
