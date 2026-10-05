"""Browser tools: click, fill, and the token-gated commit (submit).

Public functions are async (the MCP server awaits them); all Playwright
work hops to the dedicated browser thread (see browser_thread).
"""

from mcp_server import context
from mcp_server.browser_thread import run_browser
from mcp_server.schemas.tools import BrowserClickInput, BrowserFillInput, BrowserSubmitInput
from mcp_server.tools.browser.session_tools import _fresh_or_stale, _observe_dict

# Submit-scope label → effect (forms and their confirm dialogs).
FORM_EFFECTS = {
    "Create replacement": "replacement.create",
    "Confirm replacement": "replacement.create",
    "Create refund": "refund.create",
    "Confirm refund": "refund.create",
    "Add internal note": "ticket.note",
    "Reply to customer": "ticket.reply",
    "Change ticket status": "ticket.status",
}


def _click_impl(task_id: str, ref: str) -> dict:
    args = BrowserClickInput(task_id=task_id, ref=ref)
    context.store().check(args.task_id, "browser")
    session = context.browser_manager().get(args.task_id)
    _fresh_or_stale(args.task_id, session)
    session.click(args.ref)
    return _observe_dict(args.task_id, session)


async def browser_click(task_id: str, ref: str) -> dict:
    """Click a ref (page state only), then serve a fresh observation."""
    return await run_browser(_click_impl, task_id, ref)


def _fill_impl(task_id: str, ref: str, value: str) -> dict:
    args = BrowserFillInput(task_id=task_id, ref=ref, value=value)
    context.store().check(args.task_id, "browser")
    session = context.browser_manager().get(args.task_id)
    _fresh_or_stale(args.task_id, session)
    session.fill(args.ref, args.value)
    return _observe_dict(args.task_id, session)


async def browser_fill(task_id: str, ref: str, value: str) -> dict:
    """Fill a ref (form state only), then serve a fresh observation."""
    return await run_browser(_fill_impl, task_id, ref, value)


def _submit_impl(task_id: str, ref: str, mutation_key: str, token: str, params: dict) -> dict:
    """Commit the effect form behind a ref. The ONLY write path.

    Order: capability (browser + effect) → HMAC token over the exact
    params → form-effect match → idempotency interception → click →
    captured HTTP status. Transport failures raise; HTTP outcomes
    (201/409/422/500) return as data for the agent to classify.
    """
    from mcp_server import token_guard

    args = BrowserSubmitInput(
        task_id=task_id, ref=ref, mutation_key=mutation_key, token=token, params=params
    )
    store = context.store()
    store.check(args.task_id, "browser")
    effect = args.params.get("effect", "")
    store.check(args.task_id, effect)
    token_guard.verify_submit_token(args.token, context.policy_secret(), args.task_id, args.params)

    session = context.browser_manager().get(args.task_id)
    fresh = _fresh_or_stale(args.task_id, session)
    target = fresh.refs.get(args.ref)
    if target is None:
        from browser.errors import ElementNotFound

        raise ElementNotFound(f"unknown ref {args.ref} — observe explicitly, then act")
    form_label = (target.extra or {}).get("form", "")
    if FORM_EFFECTS.get(form_label) != effect:
        from mcp_server.capabilities import CapabilityDenied

        raise CapabilityDenied(
            f"capability_denied: ref is in '{form_label}', not a '{effect}' form"
        )

    page = session._page
    before_shot = session.screenshot("before-submit")

    def inject_key(route) -> None:
        request = route.request
        if request.method == "POST":
            headers = dict(request.headers)
            headers["Idempotency-Key"] = args.mutation_key
            route.continue_(headers=headers)
        else:
            route.continue_()

    page.route("**/api/ops/**", inject_key)
    try:
        try:
            with page.expect_response(
                lambda response: "/api/ops/" in response.url and response.request.method == "POST",
                timeout=session.action_timeout_ms,
            ) as response_info:
                session.click(args.ref)
            response = response_info.value
        except Exception as exc:
            from playwright.sync_api import TimeoutError as PlaywrightTimeout

            if isinstance(exc, PlaywrightTimeout):
                raise RuntimeError(
                    f"no commit POST fired for {effect!r}: the ref is not an open "
                    "confirm button (open the ticket form, fill it, press Review, "
                    "then submit the Confirm button's ref)"
                ) from exc
            raise
        try:
            body = response.text()[:2000]
        except Exception:
            body = ""
        status = response.status
    finally:
        page.unroute("**/api/ops/**")
    after_shot = session.screenshot("after-submit")
    result = {
        "ok": status < 400,
        "status": status,
        "mutation_key": args.mutation_key,
        "effect": effect,
        "body": body,
        "before_screenshot": before_shot,
        "after_screenshot": after_shot,
    }
    _observe_dict(args.task_id, session)
    return result


async def browser_submit(
    task_id: str, ref: str, mutation_key: str, token: str, params: dict
) -> dict:
    """Commit the effect form (token-gated; the only write path)."""
    return await run_browser(_submit_impl, task_id, ref, mutation_key, token, params)
