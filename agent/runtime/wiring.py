"""Default service wiring from the environment (nodes call these).

Nodes stay thin and import no repositories, adapters, or LLM clients
(architecture gate): all construction lives here. Tests monkeypatch
these factories; the runner (Phase 16) replaces them with DI.
"""

import os

from agent.adapters.mcp_gateway import MCPToolGateway
from agent.llm.client import MercuryClient, config_from_env
from agent.services.contract_service import ContractService
from agent.services.understanding_service import UnderstandingService
from database import session as session_factory


def understanding_service() -> UnderstandingService:
    """Understanding over Mercury 2.5 (INCEPTION_* env)."""
    return UnderstandingService(MercuryClient(config_from_env()))


def contract_service() -> ContractService:
    """Contract pipeline: understanding + MCP reads + `ns_runner` writes."""
    gateway = MCPToolGateway(os.environ.get("MCP_URL", "http://127.0.0.1:8002"))
    sessions = lambda: session_factory.session_for(session_factory.runner_engine())  # noqa: E731
    return ContractService(understanding_service(), gateway, sessions)
