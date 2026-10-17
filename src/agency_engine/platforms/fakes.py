"""Hermetic Fake platform adapters for isolated local execution and testing."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from agency_engine.domain.enums import ActionType, PlatformName
from agency_engine.domain.exceptions import CredentialError, PlatformApiError
from agency_engine.domain.models import ActionProposal, PlatformResource, RawSnapshot
from agency_engine.platforms.base import AdsPlatform


class FakePlatformAdapter(AdsPlatform):
    """Deterministic fake adapter that mimics real ad platform behavior."""

    def __init__(
        self,
        platform_name: PlatformName,
        client_slug: str = "global_brand",
        api_version: str = "v1.0-fake",
        valid_credentials: bool = True,
        simulate_rate_limit: bool = False,
    ) -> None:
        self.platform_name = platform_name
        self.client_slug = client_slug
        self.api_version = api_version
        self.valid_credentials = valid_credentials
        self.simulate_rate_limit = simulate_rate_limit

        # In-memory resource store
        self.resources: dict[str, PlatformResource] = {
            "camp_101": PlatformResource(
                platform=platform_name,
                account_id="acc_default",
                resource_id="camp_101",
                name=f"{platform_name.value.title()} Top Funnel Prospecting",
                status="ACTIVE",
                daily_budget=Decimal("150.00"),
                currency="USD",
            ),
            "camp_102": PlatformResource(
                platform=platform_name,
                account_id="acc_default",
                resource_id="camp_102",
                name=f"{platform_name.value.title()} Retargeting Promo",
                status="ACTIVE",
                daily_budget=Decimal("50.00"),
                currency="USD",
            ),
        }

    async def validate_credentials(self) -> bool:
        if not self.valid_credentials:
            raise CredentialError(f"Invalid credentials for {self.platform_name.value}")
        return True

    async def fetch_snapshots(
        self,
        account_id: str,
        date_preset: str = "yesterday",
        trace_id: str = "",
    ) -> RawSnapshot:
        await self.validate_credentials()
        if self.simulate_rate_limit:
            raise PlatformApiError(
                platform=self.platform_name.value,
                status_code=429,
                message="Rate limit exceeded simulation",
                is_transient=True,
                retry_after=1.0,
            )

        tid = trace_id or f"trace_{uuid.uuid4().hex[:8]}"

        # Craft realistic raw payload matching the platform's schema
        raw_rows: list[dict[str, Any]] = []
        for rid, res in self.resources.items():
            if self.platform_name == PlatformName.META:
                raw_rows.append(
                    {
                        "campaign_id": rid,
                        "campaign_name": res.name,
                        "spend": "120.50",
                        "impressions": "15400",
                        "clicks": "420",
                        "actions": [{"action_type": "purchase", "value": "12"}],
                        "date_start": "2026-10-16",
                        "date_stop": "2026-10-16",
                    }
                )
            elif self.platform_name == PlatformName.GOOGLE_ADS:
                raw_rows.append(
                    {
                        "campaign": {"id": rid, "name": res.name},
                        "metrics": {
                            "cost_micros": "120500000",
                            "impressions": 14200,
                            "clicks": 390,
                            "conversions": 10.0,
                        },
                        "segments": {"date": "2026-10-16"},
                    }
                )
            elif self.platform_name == PlatformName.LINKEDIN:
                raw_rows.append(
                    {
                        "pivotValues": [f"urn:li:sponsoredCampaign:{rid}"],
                        "campaign_name": res.name,
                        "costInLocalCurrency": "145.00",
                        "impressions": 8500,
                        "clicks": 180,
                        "externalWebsiteConversions": 4,
                        "dateRange": {"start": {"year": 2026, "month": 10, "day": 16}},
                    }
                )
            elif self.platform_name == PlatformName.TIKTOK:
                raw_rows.append(
                    {
                        "dimensions": {"campaign_id": rid, "stat_time_day": "2026-10-16"},
                        "metrics": {
                            "campaign_name": res.name,
                            "stat_cost": "95.00",
                            "show_cnt": "22000",
                            "click_cnt": "510",
                            "conversion": "14",
                        },
                    }
                )
            elif self.platform_name == PlatformName.SNAPCHAT:
                raw_rows.append(
                    {
                        "campaign_id": rid,
                        "campaign_name": res.name,
                        "spend": 85000000,  # micros
                        "impressions": 19000,
                        "swipes": 480,
                        "conversion_purchases": 8,
                        "date": "2026-10-16",
                    }
                )

        return RawSnapshot(
            snapshot_id=f"snap_{uuid.uuid4().hex[:10]}",
            client_slug=self.client_slug,
            platform=self.platform_name,
            account_id=account_id,
            fetched_at=datetime.now(UTC),
            raw_payload={"data": raw_rows, "account_id": account_id},
            trace_id=tid,
        )

    async def get_resource(
        self,
        account_id: str,
        resource_id: str,
    ) -> PlatformResource | None:
        return self.resources.get(resource_id)

    async def preview_action(
        self,
        proposal: ActionProposal,
    ) -> dict[str, Any]:
        res = self.resources.get(proposal.resource_id)
        if not res:
            return {"status": "NOT_FOUND", "message": f"Resource {proposal.resource_id} not found"}

        return {
            "status": "VALID",
            "action": proposal.action.value,
            "resource_id": proposal.resource_id,
            "current_value": str(res.daily_budget if proposal.action == ActionType.UPDATE_BUDGET else res.status),
            "intended_value": str(proposal.new_value),
            "simulated": True,
        }

    async def execute_action(
        self,
        proposal: ActionProposal,
        idempotency_key: str,
    ) -> dict[str, Any]:
        res = self.resources.get(proposal.resource_id)
        if not res:
            raise PlatformApiError(
                platform=self.platform_name.value,
                status_code=404,
                message=f"Resource {proposal.resource_id} not found",
            )

        old_val = res.daily_budget if proposal.action == ActionType.UPDATE_BUDGET else res.status

        if proposal.action == ActionType.UPDATE_BUDGET:
            res.daily_budget = Decimal(str(proposal.new_value))
        elif proposal.action == ActionType.PAUSE:
            res.status = "PAUSED"
        elif proposal.action == ActionType.ENABLE:
            res.status = "ACTIVE"

        res.updated_at = datetime.now(UTC)

        return {
            "success": True,
            "idempotency_key": idempotency_key,
            "resource_id": proposal.resource_id,
            "previous_value": str(old_val),
            "applied_value": str(proposal.new_value),
            "updated_at": res.updated_at.isoformat(),
        }
