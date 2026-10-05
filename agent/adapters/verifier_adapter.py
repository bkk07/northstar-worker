"""Verifier adapter: the agent-side seam to the independent verifier.

The adapter owns sessions and persistence (`worker.snapshots`,
`worker.verification_results` via the runner role). The `verifier/`
package itself only computes over plain data, so independence holds by
construction: this adapter imports `verifier`, never the reverse.
"""

from datetime import UTC, datetime
from uuid import UUID

from agent.ports.verifier_port import VerificationResult
from database.models.worker.evidence import Snapshot
from database.models.worker.evidence import VerificationResult as ResultRow
from verifier import service as verifier_service
from verifier.snapshot import take_snapshot

BEFORE = "before"


class VerifierAdapter:
    """Snapshot before the run, verify after it (first before-snapshot wins)."""

    def __init__(self, runner_session_factory, verifier_session_factory):
        """Two factories: reads via the read-only role, writes via runner."""
        self._runner_sessions = runner_session_factory
        self._verifier_sessions = verifier_session_factory

    def snapshot_before(self, contract: dict, run_id: str) -> dict:
        """Take and persist the before-snapshot at contract lock."""
        existing = self._load_snapshot(run_id)
        if existing is not None:
            return existing
        with self._verifier_sessions() as session:
            snap = take_snapshot(session, (contract or {}).get("snapshot_scope", {}))
        with self._runner_sessions() as session:
            session.add(Snapshot(run_id=UUID(run_id), phase=BEFORE, data=snap))
            session.commit()
        return snap

    def verify(self, contract: dict, run_id: str) -> VerificationResult:
        """After-snapshot, invariants, persisted verdict (plain data)."""
        before = self._load_snapshot(run_id)
        with self._verifier_sessions() as session:
            after = take_snapshot(session, (contract or {}).get("snapshot_scope", {}))
        outcome = verifier_service.verify_contract(contract or {}, before, after)
        with self._runner_sessions() as session:
            session.add(
                ResultRow(
                    run_id=UUID(run_id),
                    verdict=outcome["verdict"],
                    invariants={"invariants": outcome["invariants"]},
                    diff=outcome["diff"],
                    computed_at=datetime.now(UTC),
                )
            )
            session.commit()
        return {
            "verdict": outcome["verdict"],
            "invariants": outcome["invariants"],
            "diff": outcome["diff"],
        }

    def _load_snapshot(self, run_id: str) -> dict | None:
        """Latest before-snapshot for the run, if the contract locked one."""
        with self._runner_sessions() as session:
            row = (
                session.query(Snapshot)
                .filter(Snapshot.run_id == UUID(run_id), Snapshot.phase == BEFORE)
                .order_by(Snapshot.id)
                .first()
            )
            return dict(row.data) if row is not None else None
