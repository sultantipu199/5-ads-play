"""Cross-platform metric normalization engine."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import structlog

from agency_engine.domain.enums import PlatformName
from agency_engine.domain.models import CanonicalMetric, RawSnapshot
from agency_engine.ingestion.currency import CurrencyConverter

logger = structlog.get_logger()


class MetricNormalizer:
    """Normalizes vendor-specific raw payloads into unified CanonicalMetric models."""

    def __init__(self, currency_converter: CurrencyConverter | None = None) -> None:
        self.fx = currency_converter or CurrencyConverter()

    def normalize(
        self,
        snapshot: RawSnapshot,
        target_currency: str = "USD",
        timezone_str: str = "UTC",
    ) -> list[CanonicalMetric]:
        platform = snapshot.platform
        payload = snapshot.raw_payload
        data_rows = payload.get("data", [])
        if not data_rows and "results" in payload:
            data_rows = payload.get("results", [])

        normalized: list[CanonicalMetric] = []
        now = datetime.now(UTC)
        freshness_minutes = int((now - snapshot.fetched_at).total_seconds() / 60)

        for row in data_rows:
            try:
                metric = self._normalize_row(
                    platform=platform,
                    client_slug=snapshot.client_slug,
                    account_id=snapshot.account_id,
                    row=row,
                    target_currency=target_currency,
                    timezone_str=timezone_str,
                    freshness_minutes=freshness_minutes,
                    trace_id=snapshot.trace_id,
                )
                if metric:
                    normalized.append(metric)
            except Exception as exc:
                logger.error(
                    "normalization_row_error",
                    platform=platform.value,
                    error=str(exc),
                    row=row,
                )
                continue

        return normalized

    def _normalize_row(
        self,
        platform: PlatformName,
        client_slug: str,
        account_id: str,
        row: dict[str, Any],
        target_currency: str,
        timezone_str: str,
        freshness_minutes: int,
        trace_id: str,
    ) -> CanonicalMetric | None:
        if platform == PlatformName.META:
            spend_dec = Decimal(str(row.get("spend", "0")))
            actions = row.get("actions", [])
            conversions_val = Decimal("0")
            for act in actions:
                if act.get("action_type") in {"purchase", "offsite_conversion.fb_pixel_purchase"}:
                    conversions_val += Decimal(str(act.get("value", 0)))

            return CanonicalMetric(
                client_slug=client_slug,
                platform=platform,
                account_id=account_id,
                campaign_id=str(row.get("campaign_id", "unknown")),
                campaign_name=str(row.get("campaign_name", "Meta Campaign")),
                local_date=str(row.get("date_start", "2026-10-16")),
                timezone=timezone_str,
                spend=spend_dec,
                impressions=int(row.get("impressions", 0)),
                clicks=int(row.get("clicks", 0)),
                conversions=conversions_val,
                conversion_type="meta_pixel_purchase",
                attribution_window="7d_click_1d_view",
                original_currency="USD",
                reporting_currency=target_currency,
                fx_rate=self.fx.get_fx_rate("USD", target_currency),
                data_freshness_minutes=freshness_minutes,
                trace_id=trace_id,
            )

        elif platform == PlatformName.GOOGLE_ADS:
            # Handles REST searchStream format
            camp = row.get("campaign", {})
            metrics = row.get("metrics", {})
            segments = row.get("segments", {})
            cost_micros = Decimal(str(metrics.get("cost_micros", 0)))
            spend_dec = cost_micros / Decimal("1000000")

            return CanonicalMetric(
                client_slug=client_slug,
                platform=platform,
                account_id=account_id,
                campaign_id=str(camp.get("id", "unknown")),
                campaign_name=str(camp.get("name", "Google Campaign")),
                local_date=str(segments.get("date", "2026-10-16")),
                timezone=timezone_str,
                spend=spend_dec,
                impressions=int(metrics.get("impressions", 0)),
                clicks=int(metrics.get("clicks", 0)),
                conversions=Decimal(str(metrics.get("conversions", 0))),
                conversion_type="google_conversion",
                attribution_window="30d_click",
                original_currency="USD",
                reporting_currency=target_currency,
                fx_rate=self.fx.get_fx_rate("USD", target_currency),
                data_freshness_minutes=freshness_minutes,
                trace_id=trace_id,
            )

        elif platform == PlatformName.LINKEDIN:
            spend_dec = Decimal(str(row.get("costInLocalCurrency", 0)))
            pivots = row.get("pivotValues", ["camp_unknown"])
            camp_id = pivots[0].split(":")[-1] if pivots else "unknown"

            return CanonicalMetric(
                client_slug=client_slug,
                platform=platform,
                account_id=account_id,
                campaign_id=camp_id,
                campaign_name=str(row.get("campaign_name", f"LinkedIn Campaign {camp_id}")),
                local_date="2026-10-16",
                timezone=timezone_str,
                spend=spend_dec,
                impressions=int(row.get("impressions", 0)),
                clicks=int(row.get("clicks", 0)),
                conversions=Decimal(str(row.get("externalWebsiteConversions", 0))),
                conversion_type="linkedin_site_conversion",
                attribution_window="30d_click_1d_view",
                original_currency="USD",
                reporting_currency=target_currency,
                fx_rate=self.fx.get_fx_rate("USD", target_currency),
                data_freshness_minutes=freshness_minutes,
                trace_id=trace_id,
            )

        elif platform == PlatformName.TIKTOK:
            dims = row.get("dimensions", {})
            metrics = row.get("metrics", {})
            spend_dec = Decimal(str(metrics.get("stat_cost", 0)))

            return CanonicalMetric(
                client_slug=client_slug,
                platform=platform,
                account_id=account_id,
                campaign_id=str(dims.get("campaign_id", "unknown")),
                campaign_name=str(metrics.get("campaign_name", "TikTok Campaign")),
                local_date=str(dims.get("stat_time_day", "2026-10-16")),
                timezone=timezone_str,
                spend=spend_dec,
                impressions=int(metrics.get("show_cnt", 0)),
                clicks=int(metrics.get("click_cnt", 0)),
                conversions=Decimal(str(metrics.get("conversion", 0))),
                conversion_type="tiktok_web_conversion",
                attribution_window="7d_click_1d_view",
                original_currency="USD",
                reporting_currency=target_currency,
                fx_rate=self.fx.get_fx_rate("USD", target_currency),
                data_freshness_minutes=freshness_minutes,
                trace_id=trace_id,
            )

        elif platform == PlatformName.SNAPCHAT:
            raw_spend = Decimal(str(row.get("spend", 0)))
            spend_dec = raw_spend / Decimal("1000000") if raw_spend > 10000 else raw_spend

            return CanonicalMetric(
                client_slug=client_slug,
                platform=platform,
                account_id=account_id,
                campaign_id=str(row.get("campaign_id", "unknown")),
                campaign_name=str(row.get("campaign_name", "Snapchat Campaign")),
                local_date=str(row.get("date", "2026-10-16")),
                timezone=timezone_str,
                spend=spend_dec,
                impressions=int(row.get("impressions", 0)),
                clicks=int(row.get("swipes", 0)),
                conversions=Decimal(str(row.get("conversion_purchases", 0))),
                conversion_type="snap_pixel_purchase",
                attribution_window="28d_click_1d_view",
                original_currency="USD",
                reporting_currency=target_currency,
                fx_rate=self.fx.get_fx_rate("USD", target_currency),
                data_freshness_minutes=freshness_minutes,
                trace_id=trace_id,
            )

        return None
