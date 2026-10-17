"""LinkedIn Ads API adapter."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from agency_engine.domain.enums import ActionType, PlatformName
from agency_engine.domain.models import ActionProposal, PlatformResource, RawSnapshot
from agency_engine.platforms.base import AdsPlatform, ResilientHttpClient


class LinkedInPlatformAdapter(AdsPlatform):
    platform_name = PlatformName.LINKEDIN
    api_version = "v2"
    base_url = "https://api.linkedin.com/rest"

    def __init__(
        self,
        access_token: str,
        client_slug: str = "global_brand",
        http_client: ResilientHttpClient | None = None,
    ) -> None:
        self.access_token = access_token
        self.client_slug = client_slug
        self.http = http_client or ResilientHttpClient("linkedin", concurrency=3)

    async def validate_credentials(self) -> bool:
        url = f"{self.base_url}/me"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "LinkedIn-Version": "202401",
        }
        resp = await self.http.request("GET", url, headers=headers)
        return resp.status_code == 200

    async def fetch_snapshots(
        self,
        account_id: str,
        date_preset: str = "yesterday",
        trace_id: str = "",
    ) -> RawSnapshot:
        url = f"{self.base_url}/adAnalyticsV2"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "LinkedIn-Version": "202401",
        }
        params = {
            "q": "analytics",
            "pivot": "CAMPAIGN",
            "dateRange.start.day": 16,
            "dateRange.start.month": 10,
            "dateRange.start.year": 2026,
            "timeGranularity": "DAILY",
        }
        resp = await self.http.request("GET", url, headers=headers, params=params)
        data = resp.json()
        tid = trace_id or f"li_tr_{uuid.uuid4().hex[:8]}"

        return RawSnapshot(
            snapshot_id=f"snap_li_{uuid.uuid4().hex[:8]}",
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
            name=f"LinkedIn Campaign {resource_id}",
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
        url = f"{self.base_url}/adCampaignsV2/{proposal.resource_id}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "LinkedIn-Version": "202401",
        }
        payload: dict[str, Any] = {}
        if proposal.action == ActionType.PAUSE:
            payload["status"] = "PAUSED"
        elif proposal.action == ActionType.ENABLE:
            payload["status"] = "ACTIVE"
        resp = await self.http.request("POST", url, headers=headers, json_data=payload)
        res_data: dict[str, Any] = resp.json()
        return res_data
