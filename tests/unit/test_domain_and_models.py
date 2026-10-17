"""Unit tests for domain models, properties, and exceptions."""

from decimal import Decimal

from agency_engine.domain.enums import PlatformName
from agency_engine.domain.models import CanonicalMetric


def test_canonical_metric_cpa_calculation() -> None:
    metric = CanonicalMetric(
        client_slug="global_brand",
        platform=PlatformName.META,
        account_id="act_123",
        campaign_id="camp_001",
        campaign_name="Test Campaign",
        local_date="2026-10-16",
        timezone="Asia/Riyadh",
        spend=Decimal("100.00"),
        impressions=1000,
        clicks=50,
        conversions=Decimal("10.0"),
        conversion_type="purchase",
        attribution_window="7d_click_1d_view",
        original_currency="USD",
        reporting_currency="SAR",
        fx_rate=Decimal("3.75"),
        trace_id="tr_1",
    )

    # converted_spend = 100 * 3.75 = 375 SAR
    assert metric.converted_spend == Decimal("375.0000")
    # cpa = 375 / 10 = 37.50 SAR
    assert metric.cpa == Decimal("37.5000")
    # ctr = (50 / 1000) * 100 = 5.0%
    assert metric.ctr == 5.0


def test_canonical_metric_zero_conversions_cpa() -> None:
    metric = CanonicalMetric(
        client_slug="global_brand",
        platform=PlatformName.GOOGLE_ADS,
        account_id="acc_1",
        campaign_id="c_1",
        campaign_name="Zero Conv Campaign",
        local_date="2026-10-16",
        timezone="UTC",
        spend=Decimal("50.00"),
        impressions=500,
        clicks=20,
        conversions=Decimal("0.0"),
        trace_id="tr_2",
    )
    assert metric.cpa is None
