"""Graph skeleton: topology, compilation, and stub paths (Phase 12).

Stub services drive every edge, so these tests run the real compiled
graph end to end with canned states — the manual "print the path" check,
as an assertion.
"""

from agent.graph.builder import NODE_NAMES, build_graph


def _path(graph, state):
    """Node names visited by one run, in order."""
    visited = []
    for chunk in graph.stream(state, stream_mode="updates"):
        visited.extend(chunk.keys())
    return visited


def test_all_fifteen_nodes_registered():
    """The skeleton exposes every §13 node (services attach later)."""
    assert len(NODE_NAMES) == 15
    assert set(build_graph().get_graph().nodes) >= set(NODE_NAMES)


def test_unsupported_contract_path():
    """understand → contract → finalize(INCONCLUSIVE)."""
    graph = build_graph()
    final = graph.invoke(
        {
            "task_id": "t1",
            "run_id": "r1",
            "task_text": "do the impossible",
            "contract_status": "unsupported",
        }
    )
    assert _path(
        graph,
        {
            "task_id": "t1",
            "run_id": "r1",
            "task_text": "do the impossible",
            "contract_status": "unsupported",
        },
    ) == ["understand", "contract", "finalize"]
    assert final["status"] == "inconclusive"


def test_happy_stub_path_to_verified():
    """Full spine: plan → act → observe(done) → verify → succeed."""
    graph = build_graph()
    state = {
        "task_id": "t2",
        "run_id": "r2",
        "task_text": "replace the damaged laptop",
        "observation_status": "effects_done",
    }
    assert _path(graph, state) == [
        "understand",
        "contract",
        "plan",
        "decide",
        "validate",
        "policy_check",
        "execute",
        "observe",
        "verify",
        "finalize",
    ]
    assert graph.invoke(state)["status"] == "succeeded"


def test_blocked_policy_path():
    """BLOCK ends without touching execute or observe."""
    graph = build_graph()
    visited = _path(
        graph,
        {
            "task_id": "t3",
            "run_id": "r3",
            "task_text": "refund everything",
            "policy_decision": {
                "outcome": "block",
                "rule_id": "P-REF-004",
                "reason": "stub",
            },
        },
    )
    assert visited == [
        "understand",
        "contract",
        "plan",
        "decide",
        "validate",
        "policy_check",
        "finalize",
    ]
    assert "execute" not in visited


def test_parked_clarification_ends_graph():
    """Ambiguous contracts park: the graph ends, the task does not."""
    graph = build_graph()
    final = graph.invoke(
        {
            "task_id": "t4",
            "run_id": "r4",
            "task_text": "cancel it",
            "contract_status": "ambiguous",
        }
    )
    assert _path(
        graph,
        {
            "task_id": "t4",
            "run_id": "r4",
            "task_text": "cancel it",
            "contract_status": "ambiguous",
        },
    ) == ["understand", "contract", "clarification"]
    assert final.get("status") != "succeeded"
