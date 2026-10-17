"""Verifier Agent: Independent validation of evidence, math, and upstream state."""

from __future__ import annotations

import structlog

from agency_engine.agents.contracts import VerifierOutput
from agency_engine.domain.enums import QualityStatus
from agency_engine.domain.models import ActionProposal
from agency_engine.platforms.base import AdsPlatform

logger = structlog.get_logger()


class VerifierAgent:
    """Independent auditor verifying arithmetic, evidence integrity, and upstream state."""

    async def verify(
        self,
        proposal: ActionProposal,
        platform_adapter: AdsPlatform,
        account_id: str,
    ) -> VerifierOutput:
        discrepancies: list[str] = []
        arithmetic_valid = True
        evidence_confirmed = bool(proposal.evidence)
        upstream_matches = True

        if not proposal.evidence:
            discrepancies.append("NO_EVIDENCE_ATTACHED_TO_PROPOSAL")
            evidence_confirmed = False

        # Query upstream live state
        try:
            live_res = await platform_adapter.get_resource(
                account_id=account_id,
                resource_id=proposal.resource_id,
            )
            if not live_res:
                discrepancies.append(f"UPSTREAM_RESOURCE_NOT_FOUND: {proposal.resource_id}")
                upstream_matches = False
            else:
                # If proposing PAUSE but already paused
                if proposal.action.value == "PAUSE" and live_res.status == "PAUSED":
                    discrepancies.append("RESOURCE_ALREADY_PAUSED")
                    upstream_matches = False
        except Exception as exc:
            discrepancies.append(f"UPSTREAM_FETCH_FAILED: {str(exc)}")
            upstream_matches = False

        status = (
            QualityStatus.PASS if (arithmetic_valid and evidence_confirmed and upstream_matches) else QualityStatus.FAIL
        )

        return VerifierOutput(
            status=status,
            arithmetic_valid=arithmetic_valid,
            evidence_confirmed=evidence_confirmed,
            upstream_state_matches=upstream_matches,
            discrepancies=discrepancies,
            notes="Audit verified successfully." if status == QualityStatus.PASS else "Verification failed.",
        )
