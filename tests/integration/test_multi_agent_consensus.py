"""Integration tests for multi-agent consensus workflow."""

from decimal import Decimal

import pytest

from agency_engine.agents.analyst import AnalystAgent
from agency_engine.agents.coordinator import CoordinatorAgent
from agency_engine.agents.media_buyer import MediaBuyerAgent
from agency_engine.domain.enums import AutonomyMode, PlatformName
from agency_engine.domain.models import CanonicalMetric
from agency_engine.platforms.fakes import FakePlatformAdapter


@pytest.mark.asyncio
async def test_multi_agent_consensus_read_only_block() -> None:
    # 1. Setup metrics where a campaign spends 200 SAR with 0 conversions
    metric = CanonicalMetric(
        client_slug="global_brand",
        platform=PlatformName.META,
        account_id="acc_default",
        campaign_id="camp_101",
        campaign_name="Bleeder Campaign",
        local_date="2026-10-16",
        timezone="Asia/Riyadh",
        spend=Decimal("200.00"),
        impressions=10000,
        clicks=300,
        conversions=Decimal("0.0"),
        trace_id="tr_cons",
    )

    analyst = AnalystAgent()
    analyst_out = await analyst.analyze([metric])
    assert len(analyst_out.anomalies_detected) > 0
    assert len(analyst_out.evidence) == 1

    media_buyer = MediaBuyerAgent()
    mb_out = await media_buyer.generate_proposals(analyst_out, [metric])
    assert len(mb_out.proposals) == 1
    proposal = mb_out.proposals[0]
    assert proposal.action.value == "PAUSE"

    # In READ_ONLY mode, consensus must succeed on review but block execution
    coordinator = CoordinatorAgent(autonomy_mode=AutonomyMode.READ_ONLY)
    adapter = FakePlatformAdapter(PlatformName.META)

    decision = await coordinator.evaluate_proposal_consensus(
        proposal=proposal,
        platform_adapter=adapter,
        account_id="acc_default",
        human_approved=False,
    )

    assert decision.approved is True
    assert decision.execution_permitted is False
    assert "BLOCKED_BY_READ_ONLY_MODE" in decision.block_reasons


@pytest.mark.asyncio
async def test_multi_agent_consensus_human_approval_gate() -> None:
    metric = CanonicalMetric(
        client_slug="global_brand",
        platform=PlatformName.META,
        account_id="acc_default",
        campaign_id="camp_101",
        campaign_name="Bleeder Campaign",
        local_date="2026-10-16",
        timezone="Asia/Riyadh",
        spend=Decimal("200.00"),
        impressions=10000,
        clicks=300,
        conversions=Decimal("0.0"),
        trace_id="tr_cons2",
    )

    analyst = AnalystAgent()
    analyst_out = await analyst.analyze([metric])
    media_buyer = MediaBuyerAgent()
    mb_out = await media_buyer.generate_proposals(analyst_out, [metric])
    proposal = mb_out.proposals[0]

    coordinator = CoordinatorAgent(autonomy_mode=AutonomyMode.APPROVAL_REQUIRED)
    adapter = FakePlatformAdapter(PlatformName.META)

    # Without approval
    decision_pending = await coordinator.evaluate_proposal_consensus(
        proposal=proposal,
        platform_adapter=adapter,
        account_id="acc_default",
        human_approved=False,
    )
    assert decision_pending.execution_permitted is False
    assert "AWAITING_HUMAN_OPERATOR_APPROVAL" in decision_pending.block_reasons

    # With approval
    decision_approved = await coordinator.evaluate_proposal_consensus(
        proposal=proposal,
        platform_adapter=adapter,
        account_id="acc_default",
        human_approved=True,
    )
    assert decision_approved.execution_permitted is True
    assert len(decision_approved.block_reasons) == 0
