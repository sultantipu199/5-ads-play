"""Google Ads API adapter (REST API v17)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from agency_engine.domain.enums import ActionType, PlatformName
from agency_engine.domain.models import ActionProposal, PlatformResource, RawSnapshot
from agency_engine.platforms.base import AdsPlatform, ResilientHttpClient


class GoogleAdsPlatformAdapter(AdsPlatform):
    platform_name = PlatformName.GOOGLE_ADS
    api_version = "v17"
    base_url = "https://googleads.googleapis.com"

    def __init__(
        self,
        developer_token: str,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        client_slug: str = "global_brand",
        http_client: ResilientHttpClient | None = None,
    ) -> None:
        self.developer_token = developer_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.client_slug = client_slug
        self.http = http_client or ResilientHttpClient("google_ads", concurrency=3)
        self._cached_access_token: str | None = None

    async def _get_access_token(self) -> str:
        if self._cached_access_token:
            return self._cached_access_token
        # Google OAuth token exchange
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
        }
        resp = await self.http.request("POST", token_url, params=data)
        token_data = resp.json()
        self._cached_access_token = token_data.get("access_token", "fake_token")
        return self._cached_access_token

    async def validate_credentials(self) -> bool:
        token = await self._get_access_token()
        return bool(token and self.developer_token)

    async def fetch_snapshots(
        self,
        account_id: str,
        date_preset: str = "yesterday",
        trace_id: str = "",
    ) -> RawSnapshot:
        clean_cid = account_id.replace("-", "")
        token = await self._get_access_token()
        url = f"{self.base_url}/{self.api_version}/customers/{clean_cid}/googleAds:searchStream"
        headers = {
            "Authorization": f"Bearer {token}",
            "developer-token": self.developer_token,
        }
        query = (
            "SELECT campaign.id, campaign.name, campaign.status, "
            "metrics.cost_micros, metrics.impressions, metrics.clicks, "
            "metrics.conversions, segments.date "
            "FROM campaign WHERE segments.date DURING YESTERDAY"
        )
        resp = await self.http.request("POST", url, headers=headers, json_data={"query": query})
        data = resp.json()
        tid = trace_id or f"gads_tr_{uuid.uuid4().hex[:8]}"

        return RawSnapshot(
            snapshot_id=f"snap_gads_{uuid.uuid4().hex[:8]}",
            client_slug=self.client_slug,
            platform=self.platform_name,
            account_id=account_id,
            fetched_at=datetime.now(UTC),
            raw_payload={"results": data, "account_id": account_id},
            trace_id=tid,
        )

    async def get_resource(
        self,
        account_id: str,
        resource_id: str,
    ) -> PlatformResource | None:
        clean_cid = account_id.replace("-", "")
        token = await self._get_access_token()
        url = f"{self.base_url}/{self.api_version}/customers/{clean_cid}/campaigns/{resource_id}"
        headers = {
            "Authorization": f"Bearer {token}",
            "developer-token": self.developer_token,
        }
        resp = await self.http.request("GET", url, headers=headers)
        if resp.status_code == 404:
            return None
        data = resp.json()
        return PlatformResource(
            platform=self.platform_name,
            account_id=account_id,
            resource_id=resource_id,
            name=data.get("name", "Google Campaign"),
            status=data.get("status", "UNKNOWN"),
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
        clean_cid = proposal.client_slug.replace("-", "")
        token = await self._get_access_token()
        url = f"{self.base_url}/{self.api_version}/customers/{clean_cid}/campaigns:mutate"
        headers = {
            "Authorization": f"Bearer {token}",
            "developer-token": self.developer_token,
        }
        # Build mutation payload
        operations = []
        if proposal.action == ActionType.PAUSE:
            operations.append(
                {
                    "update": {
                        "resourceName": f"customers/{clean_cid}/campaigns/{proposal.resource_id}",
                        "status": "PAUSED",
                    },
                    "updateMask": "status",
                }
            )
        elif proposal.action == ActionType.ENABLE:
            operations.append(
                {
                    "update": {
                        "resourceName": f"customers/{clean_cid}/campaigns/{proposal.resource_id}",
                        "status": "ENABLED",
                    },
                    "updateMask": "status",
                }
            )

        resp = await self.http.request("POST", url, headers=headers, json_data={"operations": operations})
        res_data: dict[str, Any] = resp.json()
        return res_data
