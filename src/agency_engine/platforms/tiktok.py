"""TikTok Marketing API adapter."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from agency_engine.domain.enums import ActionType, PlatformName
from agency_engine.domain.models import ActionProposal, PlatformResource, RawSnapshot
from agency_engine.platforms.base import AdsPlatform, ResilientHttpClient


class TikTokPlatformAdapter(AdsPlatform):
    platform_name = PlatformName.TIKTOK
    api_version = "v1.3"
    base_url = "https://business-api.tiktok.com/open_api"

    def __init__(
        self,
        access_token: str,
        client_slug: str = "global_brand",
        http_client: ResilientHttpClient | None = None,
    ) -> None:
        self.access_token = access_token
        self.client_slug = client_slug
        self.http = http_client or ResilientHttpClient("tiktok", concurrency=3)

    async def validate_credentials(self) -> bool:
        url = f"{self.base_url}/{self.api_version}/user/info/"
        headers = {"Access-Token": self.access_token}
        resp = await self.http.request("GET", url, headers=headers)
        return resp.status_code == 200

    async def fetch_snapshots(
        self,
        account_id: str,
        date_preset: str = "yesterday",
        trace_id: str = "",
    ) -> RawSnapshot:
        url = f"{self.base_url}/{self.api_version}/report/integrated/get/"
        headers = {"Access-Token": self.access_token}
        params = {
            "advertiser_id": account_id,
            "report_type": "BASIC",
            "data_level": "AUCTION_CAMPAIGN",
            "dimensions": '["campaign_id", "stat_time_day"]',
            "metrics": '["campaign_name", "stat_cost", "show_cnt", "click_cnt", "conversion"]',
            "start_date": "2026-10-16",
            "end_date": "2026-10-16",
        }
        resp = await self.http.request("GET", url, headers=headers, params=params)
        data = resp.json()
        tid = trace_id or f"tt_tr_{uuid.uuid4().hex[:8]}"

        return RawSnapshot(
            snapshot_id=f"snap_tt_{uuid.uuid4().hex[:8]}",
            client_slug=self.client_slug,
            platform=self.platform_name,
            account_id=account_id,
            fetched_at=datetime.now(UTC),
            raw_payload=data,
            trace_id=tid,
        )

    async def get_resource(
        self,
        account_id: str,
        resource_id: str,
    ) -> PlatformResource | None:
        return PlatformResource(
            platform=self.platform_name,
            account_id=account_id,
            resource_id=resource_id,
            name=f"TikTok Campaign {resource_id}",
            status="ACTIVE",
            currency="USD",
        )

    async def preview_action(
        self,
        proposal: ActionProposal,
    ) -> dict[str, Any]:
        return {
            "platform": self.platform_name.value,
            "action": proposal.action.value,
            "resource_id": proposal.resource_id,
            "intended_value": str(proposal.new_value),
            "dry_run": True,
        }

    async def execute_action(
        self,
        proposal: ActionProposal,
        idempotency_key: str,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/{self.api_version}/campaign/status/update/"
        headers = {"Access-Token": self.access_token}
        opt_status = "DISABLE" if proposal.action == ActionType.PAUSE else "ENABLE"
        payload = {
            "advertiser_id": proposal.client_slug,
            "campaign_ids": [proposal.resource_id],
            "opt_status": opt_status,
        }
        resp = await self.http.request("POST", url, headers=headers, json_data=payload)
        res_data: dict[str, Any] = resp.json()
        return res_data
