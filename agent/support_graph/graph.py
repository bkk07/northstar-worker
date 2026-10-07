"""Canonical support graph: supervisor → workflow → HITL → verify → respond."""

from functools import partial

from langgraph.graph import END, START, StateGraph

from agent.support_graph import nodes
from agent.support_graph.state import SupportGraphState

NODE_NAMES = (
    "load_ticket",
    "supervisor",
    "gather",
    "check_policy",
    "propose",
    "human_approval",
    "execute",
    "verify",
    "respond",
)


def _bind(fn, tools, llm):
    def _node(state: SupportGraphState) -> dict:
        return fn(dict(state), tools, llm)

    _node.__name__ = fn.__name__
    return _node


def build_support_graph(*, tools: dict, llm=None):
    """Compile the support graph with injected tools (testable, no globals)."""
    builder: StateGraph = StateGraph(SupportGraphState)
    builder.add_node("load_ticket", _bind(nodes.load_ticket, tools, llm))
    builder.add_node("supervisor", _bind(nodes.supervise, tools, llm))
    builder.add_node("gather", _bind(nodes.gather, tools, llm))
    builder.add_node("check_policy", _bind(nodes.check_policy, tools, llm))
    builder.add_node("propose", _bind(nodes.propose, tools, llm))
    builder.add_node("human_approval", _bind(nodes.human_gate, tools, llm))
    builder.add_node("execute", _bind(nodes.execute, tools, llm))
    builder.add_node("verify", _bind(nodes.verify, tools, llm))
    builder.add_node("respond", _bind(nodes.respond, tools, llm))

    builder.add_edge(START, "load_ticket")
    builder.add_edge("load_ticket", "supervisor")
    builder.add_conditional_edges(
        "supervisor",
        _route_supervisor,
        {"gather": "gather", "respond": "respond"},
    )
    builder.add_edge("gather", "check_policy")
    builder.add_edge("check_policy", "propose")
    builder.add_edge("propose", "human_approval")
    builder.add_conditional_edges(
        "human_approval",
        _route_approval,
        {"execute": "execute", "respond": "respond", "__end__": END},
    )
    builder.add_edge("execute", "verify")
    builder.add_conditional_edges(
        "verify",
        _route_verify,
        {"respond": "respond", "__end__": END},
    )
    builder.add_edge("respond", END)
    return builder.compile()


def _route_supervisor(state: SupportGraphState) -> str:
    if state.get("decision") in ("ask_customer", "answered", "needs_human"):
        return "respond"
    return "gather"


def _route_approval(state: SupportGraphState) -> str:
    if state.get("approval_required") and state.get("approval_status") in (None, "pending"):
        return "__end__"  # pause for HITL; resume re-enters with decision
    if state.get("decision") in ("ask_customer", "answered", "needs_human", "ineligible"):
        return "respond"
    if state.get("approval_required") and state.get("approval_status") != "approved":
        return "respond"
    if state.get("workflow") not in ("REFUND", "REPLACE", "RETURN", "CANCELLATION"):
        return "respond"
    return "execute"


def _route_verify(state: SupportGraphState) -> str:
    if state.get("decision") == "needs_human" or state.get("escalated"):
        return "__end__"
    return "respond"
