"""Compliance Agent: Platform policies and regulatory checks."""

from __future__ import annotations

import structlog

from agency_engine.agents.contracts import ComplianceOutput
from agency_engine.domain.enums import QualityStatus
from agency_engine.domain.models import ActionProposal, Evidence

logger = structlog.get_logger()


class ComplianceAgent:
    """Verifies proposals against advertising policies, spend caps, and account restrictions."""

    def __init__(self, max_allowed_daily_budget_sar: float = 2000.0) -> None:
        self.max_daily_budget = max_allowed_daily_budget_sar

    async def verify_compliance(
        self,
        proposal: ActionProposal | None = None,
        account_flags: list[str] | None = None,
    ) -> ComplianceOutput:
        violations: list[str] = []
        restrictions: list[str] = list(account_flags or [])
        evidence: list[Evidence] = []

        if restrictions:
            violations.append(f"ACCOUNT_RESTRICTIONS_ACTIVE: {', '.join(restrictions)}")

        if proposal:
            # Check maximum budget cap
            if proposal.action.value == "UPDATE_BUDGET" and proposal.new_value is not None:
                try:
                    new_budget = float(proposal.new_value)
                    if new_budget > self.max_daily_budget:
                        violations.append(
                            f"BUDGET_CAP_EXCEEDED: Requested {new_budget} exceeds maximum allowed {self.max_daily_budget}"
                        )
                    if new_budget <= 0:
                        violations.append(f"INVALID_BUDGET: Budget must be strictly positive ({new_budget})")
                except ValueError:
                    violations.append(f"MALFORMED_BUDGET_VALUE: {proposal.new_value}")

        status = QualityStatus.PASS if not violations else QualityStatus.FAIL
        is_safe = status == QualityStatus.PASS

        return ComplianceOutput(
            status=status,
            policy_violations=violations,
            account_restrictions=restrictions,
            is_safe_to_proceed=is_safe,
            evidence=evidence,
            notes="Passed compliance checks." if is_safe else f"Violations found: {len(violations)}",
        )
