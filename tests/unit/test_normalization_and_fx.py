"""Unit tests for metric normalization and currency conversions."""

from decimal import Decimal

from agency_engine.domain.enums import PlatformName
from agency_engine.domain.models import RawSnapshot
from agency_engine.ingestion.currency import CurrencyConverter
from agency_engine.ingestion.normalizer import MetricNormalizer


def test_currency_converter_rates() -> None:
    converter = CurrencyConverter()
    # 1 USD to SAR is 3.75
    rate_usd_to_sar = converter.get_fx_rate("USD", "SAR")
    assert rate_usd_to_sar == Decimal("3.7500")

    # Identity rate
    assert converter.get_fx_rate("USD", "USD") == Decimal("1.0")


def test_metric_normalizer_meta() -> None:
    normalizer = MetricNormalizer()
    snapshot = RawSnapshot(
        snapshot_id="snap_1",
        client_slug="global_brand",
        platform=PlatformName.META,
        account_id="act_12345",
        raw_payload={
            "data": [
                {
                    "campaign_id": "meta_c1",
                    "campaign_name": "Meta Brand Awareness",
                    "spend": "250.75",
                    "impressions": 20000,
                    "clicks": 600,
                    "actions": [{"action_type": "purchase", "value": 15}],
                    "date_start": "2026-10-16",
                }
            ]
        },
        trace_id="tr_meta",
    )

    metrics = normalizer.normalize(snapshot, target_currency="SAR")
    assert len(metrics) == 1
    m = metrics[0]
    assert m.campaign_id == "meta_c1"
    assert m.spend == Decimal("250.75")
    assert m.reporting_currency == "SAR"
    assert m.fx_rate == Decimal("3.7500")
    assert m.conversions == Decimal("15")
    assert m.attribution_window == "7d_click_1d_view"


def test_metric_normalizer_google_ads() -> None:
    normalizer = MetricNormalizer()
    snapshot = RawSnapshot(
        snapshot_id="snap_2",
        client_slug="global_brand",
        platform=PlatformName.GOOGLE_ADS,
        account_id="123-456-7890",
        raw_payload={
            "results": [
                {
                    "campaign": {"id": "g_c1", "name": "Google Search High Intent"},
                    "metrics": {
                        "cost_micros": "50000000",  # 50.00 USD
                        "impressions": 5000,
                        "clicks": 250,
                        "conversions": 12.0,
                    },
                    "segments": {"date": "2026-10-16"},
                }
            ]
        },
        trace_id="tr_gads",
    )

    metrics = normalizer.normalize(snapshot, target_currency="USD")
    assert len(metrics) == 1
    m = metrics[0]
    assert m.campaign_id == "g_c1"
    assert m.spend == Decimal("50.00")
    assert m.conversions == Decimal("12.0")
    assert m.attribution_window == "30d_click"
