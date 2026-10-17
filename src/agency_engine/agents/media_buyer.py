"""Media Buyer Agent: Proposal generation for ad optimization."""

from __future__ import annotations

import hashlib
import uuid

import structlog

from agency_engine.agents.contracts import AnalystOutput, MediaBuyerOutput
from agency_engine.domain.enums import ActionType, PlatformName, RiskLevel
from agency_engine.domain.models import ActionProposal, CanonicalMetric

logger = structlog.get_logger()


class MediaBuyerAgent:
    """Constructs bounded, reversible action proposals based on analyst evidence."""

    def __init__(self, max_budget_increase_percent: float = 10.0) -> None:
        self.max_budget_increase_percent = max_budget_increase_percent

    async def generate_proposals(
        self,
        analyst_output: AnalystOutput,
        metrics: list[CanonicalMetric],
        policy_version: str = "v1.0",
    ) -> MediaBuyerOutput:
        proposals: list[ActionProposal] = []

        # Find campaigns with anomalies flagged in evidence
        for ev in analyst_output.evidence:
            if ev.metric_name == "spend_without_conversions":
                # Campaign is bleeding spend with zero results -> Propose PAUSE
                m_match = next((m for m in metrics if m.campaign_id == ev.resource_id), None)
                camp_name = m_match.campaign_name if m_match else "Flagged Campaign"
                client_slug = m_match.client_slug if m_match else "global_brand"
                platform = m_match.platform if m_match else PlatformName.META

                action_id = f"act_{uuid.uuid4().hex[:10]}"
                # Compute deterministic fingerprint
                fp_raw = f"{client_slug}:{platform.value}:{ev.resource_id}:PAUSE:PAUSED:{policy_version}"
                fingerprint = hashlib.sha256(fp_raw.encode("utf-8")).hexdigest()

                proposal = ActionProposal(
                    action_id=action_id,
                    fingerprint=fingerprint,
                    client_slug=client_slug,
                    platform=platform,
                    action=ActionType.PAUSE,
                    resource_id=ev.resource_id or "unknown",
                    resource_name=camp_name,
                    old_value="ACTIVE",
                    new_value="PAUSED",
                    reason=f"High spend without conversions detected ({ev.observed_value})",
                    evidence=[ev],
                    confidence=0.92,
                    risk=RiskLevel.LOW,  # Pausing is reversible and protects budget
                    requires_approval=True,
                )
                proposals.append(proposal)

        return MediaBuyerOutput(
            proposals=proposals,
            summary=f"Generated {len(proposals)} proposal(s) based on analyst findings.",
        )
