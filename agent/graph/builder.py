"""Graph skeleton: every node and conditional edge (plan §13).

Stub services drive every edge so the orchestration spine is testable
before any logic attaches. Later phases fill node bodies and add budget
guards; the topology here is the contract they must preserve.
"""

from langgraph.graph import END, START, StateGraph

from agent.graph import edges
from agent.graph.state import WorkerState
from agent.nodes.clarification import clarification
from agent.nodes.classify import classify
from agent.nodes.contract import contract
from agent.nodes.decide import decide
from agent.nodes.execute import execute
from agent.nodes.finalize import finalize
from agent.nodes.human_approval import human_approval
from agent.nodes.observe import observe
from agent.nodes.plan import plan
from agent.nodes.policy_check import policy_check
from agent.nodes.probe_reconcile import probe_reconcile
from agent.nodes.recover import recover
from agent.nodes.understand import understand
from agent.nodes.validate import validate
from agent.nodes.verify import verify

NODE_NAMES = (
    "understand",
    "contract",
    "plan",
    "decide",
    "validate",
    "policy_check",
    "human_approval",
    "clarification",
    "execute",
    "observe",
    "classify",
    "recover",
    "probe_reconcile",
    "verify",
    "finalize",
)


def build_graph():
    """Compile the worker graph (stub bodies, final topology)."""
    builder: StateGraph = StateGraph(WorkerState)
    builder.add_node("understand", understand)
    builder.add_node("contract", contract)
    builder.add_node("plan", plan)
    builder.add_node("decide", decide)
    builder.add_node("validate", validate)
    builder.add_node("policy_check", policy_check)
    builder.add_node("human_approval", human_approval)
    builder.add_node("clarification", clarification)
    builder.add_node("execute", execute)
    builder.add_node("observe", observe)
    builder.add_node("classify", classify)
    builder.add_node("recover", recover)
    builder.add_node("probe_reconcile", probe_reconcile)
    builder.add_node("verify", verify)
    builder.add_node("finalize", finalize)

    builder.add_edge(START, "understand")
    builder.add_edge("understand", "contract")
    builder.add_conditional_edges(
        "contract",
        edges.route_contract,
        {"plan": "plan", "clarification": "clarification", "finalize": "finalize"},
    )
    builder.add_edge("plan", "decide")
    builder.add_edge("decide", "validate")
    builder.add_conditional_edges(
        "validate",
        edges.route_validate,
        {"decide": "decide", "policy_check": "policy_check", "finalize": "finalize"},
    )
    builder.add_conditional_edges(
        "policy_check",
        edges.route_policy,
        {"execute": "execute", "human_approval": "human_approval", "finalize": "finalize"},
    )
    builder.add_conditional_edges(
        "human_approval",
        edges.route_approval,
        {"execute": "execute", "finalize": "finalize", "__end__": END},
    )
    builder.add_edge("execute", "observe")
    builder.add_conditional_edges(
        "observe",
        edges.route_observe,
        {"decide": "decide", "verify": "verify", "classify": "classify", "finalize": "finalize"},
    )
    builder.add_edge("classify", "recover")
    builder.add_conditional_edges(
        "recover",
        edges.route_recover,
        {
            "observe": "observe",
            "execute": "execute",
            "probe_reconcile": "probe_reconcile",
            "plan": "plan",
            "human_approval": "human_approval",
            "clarification": "clarification",
            "finalize": "finalize",
        },
    )
    builder.add_conditional_edges(
        "probe_reconcile",
        edges.route_probe,
        {"observe": "observe", "execute": "execute", "finalize": "finalize"},
    )
    builder.add_conditional_edges(
        "verify",
        edges.route_verify,
        {"finalize": "finalize", "recover": "recover"},
    )
    builder.add_conditional_edges(
        "clarification",
        edges.route_clarification,
        {"contract": "contract", "finalize": "finalize", "__end__": END},
    )
    builder.add_edge("finalize", END)
    return builder.compile()
