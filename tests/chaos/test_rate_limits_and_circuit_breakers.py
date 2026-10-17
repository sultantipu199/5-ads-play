"""Chaos and fault-injection tests: HTTP 429, partial outage, and stale data."""

from decimal import Decimal

import pytest

from agency_engine.domain.enums import PlatformName
from agency_engine.domain.exceptions import PlatformApiError
from agency_engine.domain.models import CanonicalMetric
from agency_engine.ingestion.fetcher import MetricFetcher
from agency_engine.platforms.fakes import FakePlatformAdapter
from agency_engine.reporting.briefing import BriefingService


@pytest.mark.asyncio
async def test_simulated_rate_limit_and_retry_exhaustion() -> None:
    adapter = FakePlatformAdapter(PlatformName.META, simulate_rate_limit=True)
    with pytest.raises(PlatformApiError) as exc_info:
        await adapter.fetch_snapshots(account_id="acc_default")

    assert exc_info.value.status_code == 429
    assert exc_info.value.is_transient is True


@pytest.mark.asyncio
async def test_partial_platform_outage_handling() -> None:
    # 1 normal adapter and 1 failing adapter
    adapter_ok = FakePlatformAdapter(PlatformName.META)
    adapter_fail = FakePlatformAdapter(PlatformName.GOOGLE_ADS, simulate_rate_limit=True)

    fetcher = MetricFetcher()
    results = await fetcher.fetch_all_platforms(
        [
            (adapter_ok, "acc_meta"),
            (adapter_fail, "acc_gads"),
        ]
    )

    assert results["partial_failure"] is True
    assert "google_ads" in results["errors"]
    assert len(results["metrics"]) > 0  # Meta metrics succeeded


def test_stale_data_warning_in_briefing() -> None:
    stale_metric = CanonicalMetric(
        client_slug="global_brand",
        platform=PlatformName.SNAPCHAT,
        account_id="acc_sc",
        campaign_id="c_sc",
        campaign_name="Snap Promo",
        local_date="2026-10-15",
        timezone="UTC",
        spend=Decimal("80.00"),
        impressions=4000,
        clicks=120,
        conversions=Decimal("5.0"),
        data_freshness_minutes=240,  # 4 hours old! Exceeds 180m threshold
        trace_id="tr_stale",
    )

    briefing = BriefingService()
    text = briefing.generate_briefing_text("Global Brand", [stale_metric], stale_threshold_minutes=180)
    assert "STALE DATA WARNING" in text
    assert "240 mins ago" in text
