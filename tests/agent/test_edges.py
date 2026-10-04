"""Conditional edges: one test per route with fake node outputs (Phase 12).

Routing is pure (state in, node name out), so every branch in §13 is
covered without a graph, LLM, or database.
"""

import pytest

from agent.graph import edges


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("ok", "plan"),
        ("ambiguous", "clarification"),
        ("unsupported", "finalize"),
        ("whatever", "finalize"),
        (None, "plan"),
    ],
)
def test_route_contract(status, expected):
    """Compiler outcome: plan, clarify, or end (unknown fails closed)."""
    state = {"contract_status": status} if status is not None else {}
    assert edges.route_contract(state) == expected


@pytest.mark.parametrize(
    ("status", "expected"),
    [("ok", "policy_check"), ("invalid", "decide"), ("whatever", "finalize")],
)
def test_route_validate(status, expected):
    """Invalid loops back with the error; unknown ends."""
    assert edges.route_validate({"validation_status": status}) == expected


@pytest.mark.parametrize(
    ("outcome", "expected"),
    [
        ("allow", "execute"),
        ("human_approval", "human_approval"),
        ("block", "finalize"),
        ("", "finalize"),
    ],
)
def test_route_policy(outcome, expected):
    """LLM has no vote: missing or unknown outcomes never execute."""
    assert edges.route_policy({"policy_decision": {"outcome": outcome}}) == expected


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("approved", "execute"),
        ("rejected", "finalize"),
        ("expired", "finalize"),
        ("pending", "__end__"),
    ],
)
def test_route_approval(status, expected):
    """Approved resumes, decided-against finalizes, pending parks."""
    assert edges.route_approval({"approval_status": status}) == expected


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("success", "decide"),
        ("effects_done", "verify"),
        ("failure", "classify"),
        ("whatever", "classify"),
    ],
)
def test_route_observe(status, expected):
    """Continue, prove, or classify (unknown is treated as failure)."""
    assert edges.route_observe({"observation_status": status}) == expected


@pytest.mark.parametrize(
    ("strategy", "expected"),
    [
        ("re_observe", "observe"),
        ("re_discover", "observe"),
        ("re_plan", "plan"),
        ("retry", "execute"),
        ("probe", "probe_reconcile"),
        ("reconcile", "observe"),
        ("fallback_tool", "execute"),
        ("alternate_tool", "execute"),
        ("request_approval", "human_approval"),
        ("request_clarification", "clarification"),
        ("terminate_safely", "finalize"),
        ("whatever", "finalize"),
        ("", "finalize"),
    ],
)
def test_route_recover(strategy, expected):
    """All 11 router strategies map; unknown terminates safely."""
    assert edges.route_recover({"recovery": {"strategy": strategy}}) == expected


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("exists", "observe"),
        ("absent", "execute"),
        ("mismatch", "finalize"),
        ("whatever", "finalize"),
    ],
)
def test_route_probe(status, expected):
    """Found reconciles, absent retries with the same key, mismatch ends."""
    assert edges.route_probe({"probe_status": status}) == expected


@pytest.mark.parametrize(
    ("verdict", "expected"),
    [
        ("verified", "finalize"),
        ("failed", "recover"),
        ("inconclusive", "finalize"),
        ("", "finalize"),
    ],
)
def test_route_verify(verdict, expected):
    """Only FAILED re-enters recovery; anything else finalizes."""
    assert edges.route_verify({"verification": {"verdict": verdict}}) == expected


@pytest.mark.parametrize(
    ("status", "expected"),
    [("answered", "contract"), ("pending", "__end__")],
)
def test_route_clarification(status, expected):
    """Answered re-enters the compiler; otherwise the run stays parked."""
    assert edges.route_clarification({"clarification_status": status}) == expected
