"""Analyst Agent: Read-only metric analysis and anomaly detection."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import structlog

from agency_engine.agents.contracts import AnalystOutput
from agency_engine.domain.enums import QualityStatus
from agency_engine.domain.models import CanonicalMetric, Evidence

logger = structlog.get_logger()


class AnalystAgent:
    """Analyzes normalized ad metrics, detects anomalies, and outputs evidence."""

    def __init__(self, cpa_spike_threshold_sar: Decimal = Decimal("150.0")) -> None:
        self.cpa_spike_threshold = cpa_spike_threshold_sar

    async def analyze(self, metrics: list[CanonicalMetric]) -> AnalystOutput:
        if not metrics:
            return AnalystOutput(
                status=QualityStatus.WARNING,
                data_quality_score=0.0,
                anomalies_detected=["NO_METRICS_AVAILABLE"],
                notes="Zero metrics were provided for analysis.",
            )

        evidence: list[Evidence] = []
        anomalies: list[str] = []
        kpis: dict[str, dict[str, Any]] = {}
        data_quality_penalty = 0.0

        for m in metrics:
            p_key = m.platform.value
            if p_key not in kpis:
                kpis[p_key] = {
                    "total_spend": Decimal("0.0"),
                    "total_impressions": 0,
                    "total_clicks": 0,
                    "total_conversions": Decimal("0.0"),
                    "campaign_count": 0,
                }

            # Check for data quality anomalies
            if m.spend < 0:
                anomalies.append(f"NEGATIVE_SPEND_DETECTED: {m.campaign_name} ({m.spend})")
                data_quality_penalty += 0.3
            if m.clicks < 0 or m.impressions < 0:
                anomalies.append(f"NEGATIVE_ENGAGEMENT: {m.campaign_name}")
                data_quality_penalty += 0.2
            if m.data_freshness_minutes > 180:
                anomalies.append(f"STALE_DATA_WARNING: {m.campaign_name} ({m.data_freshness_minutes}m old)")
                data_quality_penalty += 0.15

            kpis[p_key]["total_spend"] += m.converted_spend
            kpis[p_key]["total_impressions"] += m.impressions
            kpis[p_key]["total_clicks"] += m.clicks
            kpis[p_key]["total_conversions"] += m.conversions
            kpis[p_key]["campaign_count"] += 1

            # Performance anomaly: high spend with zero conversions
            if m.converted_spend > Decimal("100.0") and m.conversions == Decimal("0.0"):
                anomalies.append(
                    f"ZERO_CONVERSIONS_HIGH_SPEND: {m.campaign_name} (Spend: {m.converted_spend:.2f} {m.reporting_currency})"
                )
                evidence.append(
                    Evidence(
                        platform=m.platform.value,
                        account_id=m.account_id,
                        resource_id=m.campaign_id,
                        metric_name="spend_without_conversions",
                        observed_value=m.converted_spend,
                        trace_id=m.trace_id,
                    )
                )

            # High CPA anomaly
            if m.cpa and m.cpa > self.cpa_spike_threshold:
                anomalies.append(f"CPA_SPIKE: {m.campaign_name} CPA {m.cpa:.2f} > {self.cpa_spike_threshold}")
                evidence.append(
                    Evidence(
                        platform=m.platform.value,
                        account_id=m.account_id,
                        resource_id=m.campaign_id,
                        metric_name="cpa_spike",
                        observed_value=m.cpa,
                        trace_id=m.trace_id,
                    )
                )

        quality_score = max(0.0, 1.0 - data_quality_penalty)
        status = QualityStatus.PASS if quality_score >= 0.70 else QualityStatus.FAIL

        return AnalystOutput(
            status=status,
            data_quality_score=round(quality_score, 2),
            anomalies_detected=anomalies,
            kpis_by_platform=kpis,
            evidence=evidence,
            notes=f"Analyzed {len(metrics)} canonical metrics across {len(kpis)} platforms.",
        )
