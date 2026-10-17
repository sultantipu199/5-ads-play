"""Contract tests for platform adapters and interface conformity."""

import pytest

from agency_engine.domain.enums import ActionType, PlatformName
from agency_engine.domain.models import ActionProposal
from agency_engine.platforms.base import AdsPlatform
from agency_engine.platforms.fakes import FakePlatformAdapter


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "platform_name",
    [
        PlatformName.META,
        PlatformName.GOOGLE_ADS,
        PlatformName.LINKEDIN,
        PlatformName.TIKTOK,
        PlatformName.SNAPCHAT,
    ],
)
async def test_platform_contract_conformance(platform_name: PlatformName) -> None:
    adapter: AdsPlatform = FakePlatformAdapter(platform_name=platform_name)

    # 1. Credentials
    valid = await adapter.validate_credentials()
    assert valid is True

    # 2. Fetch snapshots
    snapshot = await adapter.fetch_snapshots(account_id="acc_test", trace_id="tr_contract")
    assert snapshot.platform == platform_name
    assert snapshot.snapshot_id.startswith("snap_")
    assert "data" in snapshot.raw_payload

    # 3. Get Resource
    res = await adapter.get_resource(account_id="acc_test", resource_id="camp_101")
    assert res is not None
    assert res.resource_id == "camp_101"

    # 4. Preview action
    prop = ActionProposal(
        action_id="act_contract",
        fingerprint="fp_contract",
        client_slug="global_brand",
        platform=platform_name,
        action=ActionType.PAUSE,
        resource_id="camp_101",
        resource_name="Camp 101",
        confidence=0.9,
    )
    preview = await adapter.preview_action(proposal=prop)
    assert preview["status"] == "VALID"
    assert preview["simulated"] is True
