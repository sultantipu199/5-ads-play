"""Data ingestion orchestrator for multi-platform ad metrics."""

from __future__ import annotations

import asyncio
from typing import Any

import structlog

from agency_engine.domain.exceptions import PlatformApiError
from agency_engine.domain.models import CanonicalMetric, RawSnapshot
from agency_engine.ingestion.normalizer import MetricNormalizer
from agency_engine.platforms.base import AdsPlatform

logger = structlog.get_logger()


class MetricFetcher:
    """Orchestrates snapshot gathering and canonical metric extraction."""

    def __init__(self, normalizer: MetricNormalizer | None = None) -> None:
        self.normalizer = normalizer or MetricNormalizer()

    async def fetch_platform_data(
        self,
        platform_adapter: AdsPlatform,
        account_id: str,
        target_currency: str = "USD",
        timezone_str: str = "UTC",
    ) -> tuple[RawSnapshot | None, list[CanonicalMetric], str | None]:
        """Fetch raw snapshot and normalize metrics for a single platform."""
        try:
            snapshot = await platform_adapter.fetch_snapshots(account_id=account_id)
            metrics = self.normalizer.normalize(
                snapshot=snapshot,
                target_currency=target_currency,
                timezone_str=timezone_str,
            )
            return snapshot, metrics, None
        except PlatformApiError as exc:
            logger.error(
                "fetch_platform_error",
                platform=platform_adapter.platform_name.value,
                status_code=exc.status_code,
                error=str(exc),
            )
            return None, [], str(exc)
        except Exception as exc:
            logger.exception(
                "unexpected_fetch_error",
                platform=platform_adapter.platform_name.value,
                error=str(exc),
            )
            return None, [], str(exc)

    async def fetch_all_platforms(
        self,
        adapters_with_accounts: list[tuple[AdsPlatform, str]],
        target_currency: str = "USD",
        timezone_str: str = "UTC",
    ) -> dict[str, Any]:
        """Fetch all platforms concurrently and collate results."""
        tasks = [
            self.fetch_platform_data(adapter, acc_id, target_currency, timezone_str)
            for adapter, acc_id in adapters_with_accounts
        ]
        results = await asyncio.gather(*tasks)

        all_snapshots: list[RawSnapshot] = []
        all_metrics: list[CanonicalMetric] = []
        errors: dict[str, str] = {}

        for (adapter, _), (snap, metrics, err) in zip(adapters_with_accounts, results, strict=False):
            p_name = adapter.platform_name.value
            if snap:
                all_snapshots.append(snap)
            if metrics:
                all_metrics.extend(metrics)
            if err:
                errors[p_name] = err

        return {
            "snapshots": all_snapshots,
            "metrics": all_metrics,
            "errors": errors,
            "partial_failure": len(errors) > 0,
        }
