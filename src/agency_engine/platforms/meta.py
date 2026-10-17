"""Meta Marketing API adapter (Graph API v19.0)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from agency_engine.domain.enums import ActionType, PlatformName
from agency_engine.domain.models import ActionProposal, PlatformResource, RawSnapshot
from agency_engine.platforms.base import AdsPlatform, ResilientHttpClient

# Module-level store for virtual / sandbox executions
_virtual_meta_store: dict[str, dict[str, Any]] = {}


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

    @property
    def is_virtual(self) -> bool:
        return bool(
            self.access_token and self.access_token.startswith(("EAA_VIRTUAL", "EAA_SANDBOX", "VIRTUAL_", "mock_"))
        )

    async def validate_credentials(self) -> bool:
        if self.is_virtual:
            return True
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
        tid = trace_id or f"meta_tr_{uuid.uuid4().hex[:8]}"

        if self.is_virtual:
            raw_rows: list[dict[str, Any]] = []
            for cid, c_data in _virtual_meta_store.items():
                is_active = c_data.get("status") == "ACTIVE"
                raw_rows.append(
                    {
                        "campaign_id": cid,
                        "campaign_name": c_data.get("name", cid),
                        "spend": "15.00" if is_active else "0.00",
                        "impressions": "1250" if is_active else "0",
                        "clicks": "68" if is_active else "0",
                        "actions": [
                            {"action_type": "onsite_conversion.messaging_conversation_started_7d", "value": "12"}
                        ]
                        if is_active
                        else [],
                        "date_start": "2026-10-17",
                        "date_stop": "2026-10-17",
                    }
                )
            return RawSnapshot(
                snapshot_id=f"snap_meta_{uuid.uuid4().hex[:8]}",
                client_slug=self.client_slug,
                platform=self.platform_name,
                account_id=account_id,
                fetched_at=datetime.now(UTC),
                raw_payload={"data": raw_rows},
                trace_id=tid,
            )

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
        if self.is_virtual:
            c_data = _virtual_meta_store.get(resource_id)
            if not c_data:
                return None
            budget_cents = c_data.get("daily_budget", 1000)
            budget = Decimal(str(budget_cents)) / Decimal("100")
            return PlatformResource(
                platform=self.platform_name,
                account_id=account_id,
                resource_id=resource_id,
                name=c_data.get("name", "Meta Campaign"),
                status=c_data.get("status", "PAUSED"),
                daily_budget=budget,
                currency="USD",
            )

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
        if self.is_virtual:
            c_data = _virtual_meta_store.get(proposal.resource_id)
            if not c_data:
                c_data = {
                    "id": proposal.resource_id,
                    "name": proposal.resource_name or "Virtual Campaign",
                    "status": "PAUSED",
                    "daily_budget": 1000,
                }
                _virtual_meta_store[proposal.resource_id] = c_data

            if proposal.action == ActionType.ENABLE:
                c_data["status"] = "ACTIVE"
            elif proposal.action == ActionType.PAUSE:
                c_data["status"] = "PAUSED"
            elif proposal.action == ActionType.UPDATE_BUDGET:
                cents = int(Decimal(str(proposal.new_value)) * 100)
                c_data["daily_budget"] = cents

            return {
                "success": True,
                "id": proposal.resource_id,
                "status": c_data["status"],
                "daily_budget": c_data.get("daily_budget"),
            }

        url = f"{self.base_url}/{self.api_version}/{proposal.resource_id}"
        payload: dict[str, Any] = {"access_token": self.access_token}
        if proposal.action == ActionType.UPDATE_BUDGET:
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

    async def create_campaign(
        self,
        account_id: str,
        name: str,
        objective: str = "OUTCOME_TRAFFIC",
        status: str = "PAUSED",
        daily_budget_cents: int | None = None,
        placement: str = "ALL",  # ALL (FB + Instagram), INSTAGRAM, FACEBOOK
        create_ad_set: bool = False,
    ) -> dict[str, Any]:
        """Create a new campaign on Meta Ads Manager (Facebook + Instagram). Defaults to PAUSED for safety."""
        clean_act = account_id if account_id.startswith("act_") else f"act_{account_id}"

        if self.is_virtual:
            cid = f"camp_meta_{uuid.uuid4().hex[:8]}"
            c_data = {
                "id": cid,
                "name": name,
                "objective": objective,
                "status": status,
                "placement": placement.upper(),
                "daily_budget": daily_budget_cents or 1000,
                "account_id": clean_act,
            }
            _virtual_meta_store[cid] = c_data
            if create_ad_set:
                as_id = f"adset_{uuid.uuid4().hex[:8]}"
                c_data["ad_set"] = {
                    "id": as_id,
                    "campaign_id": cid,
                    "name": f"{name} - {placement.title()} Set",
                    "placement": placement.upper(),
                    "status": status,
                }
            return c_data

        url = f"{self.base_url}/{self.api_version}/{clean_act}/campaigns"
        payload: dict[str, Any] = {
            "name": name,
            "objective": objective,
            "status": status,
            "special_ad_categories": [],
            "access_token": self.access_token,
        }
        if daily_budget_cents:
            payload["daily_budget"] = daily_budget_cents

        resp = await self.http.request("POST", url, json_data=payload)
        res_data: dict[str, Any] = resp.json()
        if "id" in res_data:
            res_data["placement"] = placement
            if create_ad_set:
                try:
                    ad_set = await self.create_ad_set(
                        account_id=clean_act,
                        campaign_id=res_data["id"],
                        name=f"{name} - {placement.title()} Set",
                        daily_budget_cents=daily_budget_cents or 1000,
                        placement=placement,
                        status=status,
                    )
                    res_data["ad_set"] = ad_set
                except Exception as exc:
                    res_data["ad_set_warning"] = str(exc)
        return res_data

    async def create_ad_set(
        self,
        account_id: str,
        campaign_id: str,
        name: str,
        daily_budget_cents: int = 1000,
        placement: str = "ALL",  # ALL, INSTAGRAM, FACEBOOK
        optimization_goal: str = "LINK_CLICKS",
        billing_event: str = "IMPRESSIONS",
        status: str = "PAUSED",
    ) -> dict[str, Any]:
        """Create an ad set targeting specific placements (Facebook, Instagram, or All)."""
        clean_act = account_id if account_id.startswith("act_") else f"act_{account_id}"
        placement_upper = placement.upper()

        if self.is_virtual:
            return {
                "id": f"adset_{uuid.uuid4().hex[:8]}",
                "campaign_id": campaign_id,
                "name": name,
                "daily_budget": daily_budget_cents,
                "placement": placement_upper,
                "status": status,
            }

        url = f"{self.base_url}/{self.api_version}/{clean_act}/adsets"

        if placement_upper == "INSTAGRAM":
            targeting: dict[str, Any] = {
                "geo_locations": {"countries": ["US"]},
                "publisher_platforms": ["instagram"],
                "instagram_positions": ["stream", "story", "explore", "reels"],
            }
        elif placement_upper == "FACEBOOK":
            targeting = {
                "geo_locations": {"countries": ["US"]},
                "publisher_platforms": ["facebook"],
                "facebook_positions": ["feed", "story", "marketplace"],
            }
        else:
            targeting = {
                "geo_locations": {"countries": ["US"]},
                "publisher_platforms": ["facebook", "instagram"],
            }

        payload: dict[str, Any] = {
            "name": name,
            "campaign_id": campaign_id,
            "daily_budget": daily_budget_cents,
            "billing_event": billing_event,
            "optimization_goal": optimization_goal,
            "targeting": targeting,
            "status": status,
            "access_token": self.access_token,
        }

        resp = await self.http.request("POST", url, json_data=payload)
        res_data: dict[str, Any] = resp.json()
        if "id" in res_data:
            res_data["placement"] = placement_upper
        return res_data
