"""Unit and contract tests for Meta & Instagram Ads management."""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from agency_engine.domain.enums import MetaPlacement, PlatformName
from agency_engine.platforms.fakes import FakePlatformAdapter
from agency_engine.platforms.meta import MetaPlatformAdapter
from agency_engine.web.app import app


def test_meta_placement_enum() -> None:
    assert MetaPlacement.ALL == "ALL"
    assert MetaPlacement.INSTAGRAM == "INSTAGRAM"
    assert MetaPlacement.FACEBOOK == "FACEBOOK"


@pytest.mark.asyncio
async def test_fake_adapter_create_campaign_placements() -> None:
    adapter = FakePlatformAdapter(platform_name=PlatformName.META)

    # 1. Instagram Only Campaign
    res_ig = await adapter.create_campaign(
        account_id="act_test_ig",
        name="Spring IG Reels Drop",
        objective="OUTCOME_TRAFFIC",
        daily_budget_cents=2000,
        placement="INSTAGRAM",
        create_ad_set=True,
    )
    assert res_ig["placement"] == "INSTAGRAM"
    assert res_ig["daily_budget"] == 2000
    assert "id" in res_ig
    assert "ad_set" in res_ig
    assert res_ig["ad_set"]["placement"] == "INSTAGRAM"

    # Verify resource store
    cid = res_ig["id"]
    assert cid in adapter.resources
    assert adapter.resources[cid].daily_budget == Decimal("20.00")

    # 2. Advantage+ (Facebook + Instagram)
    res_all = await adapter.create_campaign(
        account_id="act_test_all",
        name="Omni FB & IG Promotion",
        placement="ALL",
        create_ad_set=True,
    )
    assert res_all["placement"] == "ALL"
    assert res_all["ad_set"]["placement"] == "ALL"


@pytest.mark.asyncio
async def test_meta_adapter_create_campaign_and_ad_set_mock() -> None:
    mock_http = MagicMock()

    # Mock response for campaign creation then ad set creation
    resp_campaign = httpx.Response(200, json={"id": "camp_meta_999"})
    resp_adset = httpx.Response(200, json={"id": "adset_meta_888"})
    mock_http.request = AsyncMock(side_effect=[resp_campaign, resp_adset])

    adapter = MetaPlatformAdapter(access_token="EAAFakeToken", client_slug="b_fashion_explore", http_client=mock_http)

    res = await adapter.create_campaign(
        account_id="act_2665580250239749",
        name="Summer Instagram Reels Campaign",
        objective="OUTCOME_TRAFFIC",
        daily_budget_cents=1500,
        placement="INSTAGRAM",
        create_ad_set=True,
    )

    assert res["id"] == "camp_meta_999"
    assert res["placement"] == "INSTAGRAM"
    assert res["ad_set"]["id"] == "adset_meta_888"
    assert res["ad_set"]["placement"] == "INSTAGRAM"

    # Verify HTTP calls
    assert mock_http.request.call_count == 2
    # Verify targeting payload in ad set creation
    ad_set_call_kwargs = mock_http.request.call_args_list[1][1]
    targeting = ad_set_call_kwargs["json_data"]["targeting"]
    assert targeting["publisher_platforms"] == ["instagram"]
    assert "reels" in targeting["instagram_positions"]


@pytest.mark.asyncio
async def test_api_meta_create_campaign_endpoint() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "client_slug": "b_fashion_explore",
            "name": "B-Fashion Summer Drop",
            "objective": "OUTCOME_SALES",
            "daily_budget_dollars": 25.0,
            "placement": "INSTAGRAM",
            "use_fakes": True,
        }
        resp = await client.post("/api/meta/create-campaign", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["placement"] == "INSTAGRAM"
        assert "Campaign 'B-Fashion Summer Drop'" in data["message"]


@pytest.mark.asyncio
async def test_api_virtual_token_and_status_toggle() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Generate virtual token
        tok_resp = await client.post("/api/meta/generate-virtual-token?client_slug=sandbox_test")
        assert tok_resp.status_code == 200
        tok_data = tok_resp.json()
        assert tok_data["success"] is True
        assert tok_data["token"].startswith("EAA_VIRTUAL_TOKEN")

        # 2. Create campaign via API
        create_resp = await client.post(
            "/api/meta/create-campaign",
            json={
                "client_slug": "sandbox_test",
                "name": "Messages Campaign Test",
                "objective": "OUTCOME_ENGAGEMENT",
                "daily_budget_dollars": 15.0,
                "placement": "ALL",
                "use_fakes": False,
            },
        )
        assert create_resp.status_code == 200
        c_id = create_resp.json()["data"]["id"]

        # 3. Toggle Status to ACTIVE (Run)
        run_resp = await client.post(
            "/api/campaigns/status",
            json={
                "client_slug": "sandbox_test",
                "campaign_id": c_id,
                "status": "ACTIVE",
            },
        )
        assert run_resp.status_code == 200
        assert run_resp.json()["status"] == "ACTIVE"

        # 4. Toggle Status to PAUSED (Pause)
        pause_resp = await client.post(
            "/api/campaigns/status",
            json={
                "client_slug": "sandbox_test",
                "campaign_id": c_id,
                "status": "PAUSED",
            },
        )
        assert pause_resp.status_code == 200
        assert pause_resp.json()["status"] == "PAUSED"
