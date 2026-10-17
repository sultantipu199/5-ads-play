"""Coordinator Agent: Deterministic consensus state machine."""

from __future__ import annotations

import structlog

from agency_engine.agents.analyst import AnalystAgent
from agency_engine.agents.compliance import ComplianceAgent
from agency_engine.agents.contracts import ConsensusDecision
from agency_engine.agents.media_buyer import MediaBuyerAgent
from agency_engine.agents.risk import RiskAgent
from agency_engine.agents.verifier import VerifierAgent
from agency_engine.domain.enums import AutonomyMode, QualityStatus
from agency_engine.domain.models import ActionProposal
from agency_engine.platforms.base import AdsPlatform

logger = structlog.get_logger()


class CoordinatorAgent:
    """Orchestrates multi-agent consensus before any live action can be proposed or executed."""

    def __init__(
        self,
        analyst: AnalystAgent | None = None,
        compliance: ComplianceAgent | None = None,
        media_buyer: MediaBuyerAgent | None = None,
        risk: RiskAgent | None = None,
        verifier: VerifierAgent | None = None,
        autonomy_mode: AutonomyMode = AutonomyMode.READ_ONLY,
    ) -> None:
        self.analyst = analyst or AnalystAgent()
        self.compliance = compliance or ComplianceAgent()
        self.media_buyer = media_buyer or MediaBuyerAgent()
        self.risk = risk or RiskAgent()
        self.verifier = verifier or VerifierAgent()
        self.autonomy_mode = autonomy_mode

    async def evaluate_proposal_consensus(
        self,
        proposal: ActionProposal,
        platform_adapter: AdsPlatform,
        account_id: str,
        human_approved: bool = False,
    ) -> ConsensusDecision:
        block_reasons: list[str] = []
        reasons: list[str] = []

        # 1. Compliance check
        comp_output = await self.compliance.verify_compliance(proposal=proposal)
        if comp_output.status != QualityStatus.PASS:
            block_reasons.extend(comp_output.policy_violations)
        else:
            reasons.append("Compliance check passed.")

        # 2. Risk check
        risk_output = await self.risk.evaluate_risk(proposal=proposal)
        if not risk_output.passed:
            block_reasons.extend(risk_output.risk_factors)
        else:
            reasons.append(f"Risk acceptable ({risk_output.level.value}).")

        # 3. Verifier check
        ver_output = await self.verifier.verify(
            proposal=proposal,
            platform_adapter=platform_adapter,
            account_id=account_id,
        )
        if ver_output.status != QualityStatus.PASS:
            block_reasons.extend(ver_output.discrepancies)
        else:
            reasons.append("Verifier audit confirmed.")

        # Autonomy Gate:
        # READ_ONLY: Never executes
        # SHADOW: Simulates/Generates proposal only
        # APPROVAL_REQUIRED: Needs human approval
        # LIMITED_AUTONOMY: Allowlisted low-risk actions may execute
        approved_by_agents = len(block_reasons) == 0
        execution_permitted = False

        if approved_by_agents:
            if self.autonomy_mode == AutonomyMode.READ_ONLY:
                block_reasons.append("BLOCKED_BY_READ_ONLY_MODE")
            elif self.autonomy_mode == AutonomyMode.SHADOW:
                block_reasons.append("BLOCKED_BY_SHADOW_MODE_SIMULATION_ONLY")
            elif self.autonomy_mode == AutonomyMode.APPROVAL_REQUIRED:
                if human_approved:
                    execution_permitted = True
                    reasons.append("Human approval verified.")
                else:
                    block_reasons.append("AWAITING_HUMAN_OPERATOR_APPROVAL")
            elif self.autonomy_mode == AutonomyMode.LIMITED_AUTONOMY:
                # Allowed without pre-approval only for low-risk actions
                if risk_output.level.value == "LOW" and proposal.action.value == "PAUSE":
                    execution_permitted = True
                    reasons.append("Executed under limited autonomy policy.")
                elif human_approved:
                    execution_permitted = True
                else:
                    block_reasons.append("HUMAN_APPROVAL_REQUIRED_FOR_BUDGET_CHANGES")

        return ConsensusDecision(
            action_id=proposal.action_id,
            approved=approved_by_agents,
            execution_permitted=execution_permitted,
            autonomy_mode=self.autonomy_mode.value,
            reasons=reasons,
            block_reasons=block_reasons,
            proposal=proposal,
        )
