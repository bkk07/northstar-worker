"""Default service wiring from the environment (nodes call these).

Nodes stay thin and import no repositories, adapters, or LLM clients
(architecture gate): all construction lives here. Tests monkeypatch
these factories; the runner (Phase 16) replaces them with DI.
"""

import os

from sqlalchemy.orm import Session

from agent.adapters.mcp_gateway import MCPToolGateway
from agent.llm.client import MercuryClient, config_from_env
from agent.services.contract_service import ContractService
from agent.services.decision_service import DecisionService
from agent.services.planning_service import PlanningService
from agent.services.understanding_service import UnderstandingService
from agent.services.validation_service import ValidationService
from database import session as session_factory


def understanding_service() -> UnderstandingService:
    """Understanding over Mercury 2.5 (INCEPTION_* env)."""
    return UnderstandingService(MercuryClient(config_from_env()))


def contract_service() -> ContractService:
    """Contract pipeline: understanding + MCP reads + `ns_runner` writes."""
    gateway = MCPToolGateway(os.environ.get("MCP_URL", "http://127.0.0.1:8002"))
    return ContractService(understanding_service(), gateway, _session_factory)


def planning_service() -> PlanningService:
    """Step planning over Mercury 2.5 (INCEPTION_* env)."""
    return PlanningService(MercuryClient(config_from_env()))


def decision_service() -> DecisionService:
    """Next-action choice over Mercury 2.5 (INCEPTION_* env)."""
    return DecisionService(MercuryClient(config_from_env()))


def validation_service() -> ValidationService:
    """Proposal gate with `ns_runner` journal writes."""
    return ValidationService(_session_factory)


def new_runner_session() -> Session:
    """One short-lived `ns_runner` session (node persistence)."""
    return _session_factory()


def _session_factory() -> Session:
    return session_factory.session_for(session_factory.runner_engine())
