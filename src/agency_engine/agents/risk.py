"""Risk Agent: Evaluates exposure, confidence, and blast radius."""

from __future__ import annotations

import structlog

from agency_engine.agents.contracts import RiskOutput
from agency_engine.domain.enums import ActionType, RiskLevel
from agency_engine.domain.models import ActionProposal

logger = structlog.get_logger()


class RiskAgent:
    """Scores proposal confidence, blast radius, and financial risk exposure."""

    def __init__(self, confidence_threshold: float = 0.85) -> None:
        self.confidence_threshold = confidence_threshold

    async def evaluate_risk(self, proposal: ActionProposal) -> RiskOutput:
        risk_factors: list[str] = []
        blast_radius = 0.2
        level = RiskLevel.LOW

        # Confidence gate
        if proposal.confidence < self.confidence_threshold:
            risk_factors.append(
                f"LOW_CONFIDENCE: Proposal confidence ({proposal.confidence}) < threshold ({self.confidence_threshold})"
            )

        # Budget increase assessment
        if proposal.action == ActionType.UPDATE_BUDGET:
            blast_radius = 0.5
            level = RiskLevel.MEDIUM
            if proposal.old_value and proposal.new_value:
                try:
                    old_b = float(proposal.old_value)
                    new_b = float(proposal.new_value)
                    if old_b > 0:
                        pct_increase = ((new_b - old_b) / old_b) * 100.0
                        if pct_increase > 25.0:
                            level = RiskLevel.HIGH
                            risk_factors.append(f"AGGRESSIVE_BUDGET_INCREASE: {pct_increase:.1f}%")
                            blast_radius = 0.8
                except (ValueError, TypeError):
                    risk_factors.append("MALFORMED_BUDGET_COMPARISON")

        passed = (level in {RiskLevel.LOW, RiskLevel.MEDIUM}) and (proposal.confidence >= self.confidence_threshold)

        return RiskOutput(
            level=level,
            confidence=proposal.confidence,
            blast_radius_score=blast_radius,
            passed=passed,
            risk_factors=risk_factors,
        )
