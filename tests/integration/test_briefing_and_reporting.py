"""Integration tests for briefing generation and Telegram delivery."""

from decimal import Decimal

import pytest

from agency_engine.domain.enums import ActionType, PlatformName
from agency_engine.domain.models import ActionProposal, CanonicalMetric
from agency_engine.reporting.briefing import BriefingService
from agency_engine.reporting.telegram import TelegramNotifier, escape_markdown_v2


def test_markdown_v2_escaping() -> None:
    raw = "Spend: $100.50 (Meta_Ads) - [Test!]"
    escaped = escape_markdown_v2(raw)
    assert "\\." in escaped
    assert "\\-" in escaped
    assert "\\_" in escaped
    assert "\\[" in escaped
    assert "\\]" in escaped
    assert "\\!" in escaped


@pytest.mark.asyncio
async def test_telegram_deduplication() -> None:
    notifier = TelegramNotifier(default_chat_id="12345678", dry_run=True)
    key = "daily_brief:global_brand:2026-10-17"

    # First send succeeds
    first_res = await notifier.send_message("Test message 1", dedup_key=key)
    assert first_res is True

    # Second send with same dedup_key is deduplicated (skips dispatch, returns True)
    second_res = await notifier.send_message("Test message 2", dedup_key=key)
    assert second_res is True


def test_briefing_text_formatting_with_proposals() -> None:
    metric = CanonicalMetric(
        client_slug="global_brand",
        platform=PlatformName.TIKTOK,
        account_id="acc_tt",
        campaign_id="tt_c1",
        campaign_name="TikTok Viral Wave",
        local_date="2026-10-16",
        timezone="Asia/Riyadh",
        spend=Decimal("150.00"),
        impressions=15000,
        clicks=450,
        conversions=Decimal("15.0"),
        original_currency="USD",
        reporting_currency="SAR",
        fx_rate=Decimal("3.75"),
        trace_id="tr_tt",
    )

    prop = ActionProposal(
        action_id="act_tt_opt",
        fingerprint="fp_tt_1234567890",
        client_slug="global_brand",
        platform=PlatformName.TIKTOK,
        action=ActionType.UPDATE_BUDGET,
        resource_id="tt_c1",
        resource_name="TikTok Viral Wave",
        old_value="150.00",
        new_value="165.00",
        reason="Consistent low CPA under target",
        confidence=0.95,
    )

    briefing = BriefingService()
    text = briefing.generate_briefing_text("Global Brand", [metric], [prop])
    assert "Global Brand Daily Executive Briefing" in text
    assert "TikTok Viral Wave" in text
    assert "UPDATE\\_BUDGET" in text
