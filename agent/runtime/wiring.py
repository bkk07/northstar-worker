"""Default service wiring from the environment (nodes call these).

Nodes stay thin and import no repositories, adapters, or LLM clients
(architecture gate): all construction lives here. Tests monkeypatch
these factories; the runner (Phase 16) replaces them with DI.
"""

import os
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from agent.adapters.mcp_gateway import MCPToolGateway
from agent.llm.client import MercuryClient, config_from_env
from agent.ports.clock import ClockPort, SystemClock
from agent.services.contract_service import ContractService
from agent.services.decision_service import DecisionService
from agent.services.execution_service import ExecutionService
from agent.services.finalization_service import FinalizationService
from agent.services.observation_service import ObservationService
from agent.services.planning_service import PlanningService
from agent.services.policy_service import PolicyService
from agent.services.understanding_service import UnderstandingService
from agent.services.validation_service import ValidationService
from database import session as session_factory

if TYPE_CHECKING:
    from agent.adapters.verifier_adapter import VerifierAdapter
    from agent.runtime.audit_emitter import AuditEmitter
    from agent.runtime.runner import Runner
    from agent.services.approval_service import ApprovalService
    from agent.services.clarification_service import ClarificationService
    from agent.services.reconciliation_service import ReconciliationService
    from agent.services.recovery_service import RecoveryService


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


def mcp_gateway() -> MCPToolGateway:
    """Agent-side gateway to the tool server (MCP_URL env)."""
    return MCPToolGateway(os.environ.get("MCP_URL", "http://127.0.0.1:8002"))


def system_clock() -> ClockPort:
    """Production clock (tests inject fakes at the service boundary)."""
    return SystemClock()


def policy_service() -> PolicyService:
    """Deterministic policy over the shared HMAC secret."""
    return PolicyService(
        _session_factory,
        os.environ.get("POLICY_TOKEN_SECRET", "local-policy-secret"),
        system_clock(),
    )


def execution_service() -> ExecutionService:
    """Journaled MCP dispatch (journal-first, `ns_runner` writes)."""
    return ExecutionService(_session_factory, mcp_gateway(), system_clock())


def observation_service() -> ObservationService:
    """Outcome normalization plus basic memory writes."""
    return ObservationService(_session_factory)


def finalization_service() -> FinalizationService:
    """Terminal mapping and evidence summaries (no persistence)."""
    return FinalizationService()


def audit_emitter() -> "AuditEmitter":
    """Append-only audit access for nodes and the runner."""
    from agent.runtime.audit_emitter import AuditEmitter

    return AuditEmitter(_session_factory, system_clock())


def recovery_service() -> "RecoveryService":
    """Failure-type router with counters and audit."""
    from agent.services.recovery_service import RecoveryService

    return RecoveryService(_session_factory, system_clock())


def reconciliation_service() -> "ReconciliationService":
    """Probe-before-retry for unknown commit outcomes."""
    from agent.services.reconciliation_service import ReconciliationService

    return ReconciliationService(_session_factory, mcp_gateway(), system_clock())


def runner() -> "Runner":
    """Single-process runner (graph + checkpoints + audit, no leases yet)."""
    from agent.runtime.runner import Runner

    return Runner(_session_factory, system_clock())


def new_runner_session() -> Session:
    """One short-lived `ns_runner` session (node persistence)."""
    return _session_factory()


def verifier_adapter() -> "VerifierAdapter":
    """Independent verification over the read-only role (Phase 21)."""
    from agent.adapters.verifier_adapter import VerifierAdapter

    return VerifierAdapter(_session_factory, _verifier_session_factory)


def _verifier_session_factory() -> Session:
    return session_factory.session_for(session_factory.verifier_engine())


def approval_service() -> "ApprovalService":
    """Runner-role approval park/resume with token-on-consume (Phase 22)."""
    from agent.services.approval_service import ApprovalService

    return ApprovalService(
        _session_factory,
        os.environ.get("POLICY_TOKEN_SECRET", "local-policy-secret"),
        system_clock(),
    )


def clarification_service() -> "ClarificationService":
    """Runner-role clarification park/resume (Phase 22)."""
    from agent.services.clarification_service import ClarificationService

    return ClarificationService(_session_factory, system_clock())


def _session_factory() -> Session:
    return session_factory.session_for(session_factory.runner_engine())
