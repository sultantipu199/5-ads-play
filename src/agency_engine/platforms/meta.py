"""Meta Marketing API adapter (Graph API v19.0)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from agency_engine.domain.enums import ActionType, PlatformName
from agency_engine.domain.models import ActionProposal, PlatformResource, RawSnapshot
from agency_engine.platforms.base import AdsPlatform, ResilientHttpClient


class MetaPlatformAdapter(AdsPlatform):
    platform_name = PlatformName.META
    api_version = "v19.0"
    base_url = "https://graph.facebook.com"

    def __init__(
        self,
        access_token: str,
        client_slug: str = "global_brand",
        http_client: ResilientHttpClient | None = None,
    ) -> None:
        self.access_token = access_token
        self.client_slug = client_slug
        self.http = http_client or ResilientHttpClient("meta", concurrency=3)

    async def validate_credentials(self) -> bool:
        url = f"{self.base_url}/{self.api_version}/me"
        params = {"access_token": self.access_token, "fields": "id,name"}
        resp = await self.http.request("GET", url, params=params)
        return resp.status_code == 200

    async def fetch_snapshots(
        self,
        account_id: str,
        date_preset: str = "yesterday",
        trace_id: str = "",
    ) -> RawSnapshot:
        clean_act = account_id if account_id.startswith("act_") else f"act_{account_id}"
        url = f"{self.base_url}/{self.api_version}/{clean_act}/insights"
        params = {
            "access_token": self.access_token,
            "level": "campaign",
            "fields": "campaign_id,campaign_name,spend,impressions,clicks,actions,date_start,date_stop",
            "date_preset": date_preset,
        }
        resp = await self.http.request("GET", url, params=params)
        data = resp.json()
        tid = trace_id or f"meta_tr_{uuid.uuid4().hex[:8]}"

        return RawSnapshot(
            snapshot_id=f"snap_meta_{uuid.uuid4().hex[:8]}",
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
        url = f"{self.base_url}/{self.api_version}/{resource_id}"
        params = {
            "access_token": self.access_token,
            "fields": "id,name,status,daily_budget",
        }
        resp = await self.http.request("GET", url, params=params)
        if resp.status_code == 404:
            return None
        data = resp.json()
        raw_budget = data.get("daily_budget")
        budget = (Decimal(str(raw_budget)) / Decimal("100")) if raw_budget else None
        return PlatformResource(
            platform=self.platform_name,
            account_id=account_id,
            resource_id=data.get("id", resource_id),
            name=data.get("name", "Meta Campaign"),
            status=data.get("status", "UNKNOWN"),
            daily_budget=budget,
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
        url = f"{self.base_url}/{self.api_version}/{proposal.resource_id}"
        payload: dict[str, Any] = {"access_token": self.access_token}
        if proposal.action == ActionType.UPDATE_BUDGET:
            # Meta accepts daily_budget in cents
            cents = int(Decimal(str(proposal.new_value)) * 100)
            payload["daily_budget"] = cents
        elif proposal.action == ActionType.PAUSE:
            payload["status"] = "PAUSED"
        elif proposal.action == ActionType.ENABLE:
            payload["status"] = "ACTIVE"
        else:
            return {"status": "NOOP"}

        resp = await self.http.request("POST", url, json_data=payload)
        res_data: dict[str, Any] = resp.json()
        return res_data
