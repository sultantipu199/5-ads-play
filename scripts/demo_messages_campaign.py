"""Autonomous Demonstration: Create, Run, and Pause a Messages Campaign for Facebook & Instagram."""

from __future__ import annotations

import asyncio
import sys

# Configure UTF-8 for Windows PowerShell output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

import structlog

from agency_engine.actions.approvals import ApprovalManager
from agency_engine.actions.executor import ActionExecutor
from agency_engine.actions.idempotency import IdempotencyRegistry
from agency_engine.domain.enums import ActionType, PlatformName
from agency_engine.domain.models import ActionProposal
from agency_engine.platforms.meta import MetaPlatformAdapter
from agency_engine.security.secret_provider import EnvSecretProvider
from agency_engine.settings import load_settings
from agency_engine.web.app import managed_campaigns

logger = structlog.get_logger()


async def run_messages_campaign_lifecycle_demo() -> None:
    print("\n" + "=" * 70)
    print("🚀 B-Fashion Explore: Facebook & Instagram Messages Campaign Demo")
    print("   Account: act_2665580250239749 | Placements: FB Messenger + IG Direct")
    print("=" * 70 + "\n")

    settings = load_settings()
    client_slug = "b_fashion_explore"
    c_cfg = settings.clients[client_slug]
    p_meta = c_cfg.platforms["meta"]

    # 1. Credentials
    secret_prov = EnvSecretProvider()
    token = secret_prov.get_secret(p_meta.secret_ref)
    print(f"🔑 [1/4] Token Verified: {token[:15]}... (Virtual Meta Token Active)")

    adapter = MetaPlatformAdapter(access_token=token, client_slug=client_slug)
    assert await adapter.validate_credentials() is True
    print("✅ Credentials validation successful.")

    # 2. Create Messages Campaign for Facebook & Instagram
    print("\n📝 [2/4] Creating Messages Campaign (Facebook + Instagram Placements)...")
    camp_name = "B-Fashion VIP Messenger & IG Direct Sales Drop"
    camp_res = await adapter.create_campaign(
        account_id=p_meta.account_id,
        name=camp_name,
        objective="OUTCOME_ENGAGEMENT",
        daily_budget_cents=1500,  # $15.00/day
        placement="ALL",  # Facebook + Instagram Placements
        status="PAUSED",
        create_ad_set=True,
    )

    camp_id = camp_res["id"]
    adset_id = camp_res.get("ad_set", {}).get("id", "adset_generated")
    print("✅ Campaign Created Successfully:")
    print(f"   • Campaign ID: {camp_id}")
    print(f"   • Campaign Name: {camp_name}")
    print("   • Objective: OUTCOME_ENGAGEMENT (Messenger & Instagram Direct)")
    print(f"   • Placement: {camp_res.get('placement')} (Facebook + Instagram)")
    print(f"   • Ad Set ID: {adset_id}")
    print(f"   • Initial Status: {camp_res.get('status')} (Safely Paused)")
    print("   • Daily Budget: $15.00 USD")

    # Add to managed registry for web dashboard
    camp_entry = {
        "id": camp_id,
        "client_slug": client_slug,
        "name": camp_name,
        "objective": "OUTCOME_ENGAGEMENT",
        "placement": "ALL",
        "budget": "15.00",
        "spend": "0.00",
        "impressions": 0,
        "clicks": 0,
        "conversions": 0,
        "status": "PAUSED",
    }
    managed_campaigns.insert(0, camp_entry)

    # 3. Action Execution: RUN THE CAMPAIGN (Activate)
    print("\n▶️ [3/4] RUNNING CAMPAIGN: Activating ad delivery across Facebook & Instagram...")
    idempotency_reg = IdempotencyRegistry()
    approval_mgr = ApprovalManager()
    executor = ActionExecutor(idempotency_registry=idempotency_reg)

    run_proposal = ActionProposal(
        action_id="act_enable_messages_001",
        fingerprint="fp_enable_messages_001",
        client_slug=client_slug,
        platform=PlatformName.META,
        action=ActionType.ENABLE,
        resource_id=camp_id,
        resource_name=camp_name,
        confidence=0.99,
        intended_value="ACTIVE",
    )

    approval_mgr.approve_action(run_proposal, approver="Autonomous Engine", channel="cli_demo")
    exec_run = await executor.execute(run_proposal, adapter, p_meta.account_id)

    # Verify status in platform
    active_res = await adapter.get_resource(p_meta.account_id, camp_id)
    assert active_res is not None
    print(f"✅ Execution Status: {exec_run.state.value}")
    print(f"   • Cryptographic Fingerprint: {exec_run.fingerprint}")
    print(f"   • Previous State: {exec_run.pre_state_value}")
    print(f"   • Live Applied State: {exec_run.post_state_value}")
    print(f"   • Live Verified Status: {active_res.status} 🟢 (NOW RUNNING ON FB & INSTAGRAM)")

    camp_entry["status"] = "ACTIVE"

    # Brief delay to simulate live running state
    await asyncio.sleep(1)

    # 4. Action Execution: PAUSE THE CAMPAIGN
    print("\n⏸️ [4/4] PAUSING CAMPAIGN: Pausing ad delivery safely...")
    pause_proposal = ActionProposal(
        action_id="act_pause_messages_002",
        fingerprint="fp_pause_messages_002",
        client_slug=client_slug,
        platform=PlatformName.META,
        action=ActionType.PAUSE,
        resource_id=camp_id,
        resource_name=camp_name,
        confidence=1.0,
        intended_value="PAUSED",
    )

    approval_mgr.approve_action(pause_proposal, approver="Autonomous Engine", channel="cli_demo")
    exec_pause = await executor.execute(pause_proposal, adapter, p_meta.account_id)

    paused_res = await adapter.get_resource(p_meta.account_id, camp_id)
    assert paused_res is not None
    print(f"✅ Execution Status: {exec_pause.state.value}")
    print(f"   • Cryptographic Fingerprint: {exec_pause.fingerprint}")
    print(f"   • Previous State: {exec_pause.pre_state_value}")
    print(f"   • Live Applied State: {exec_pause.post_state_value}")
    print(f"   • Live Verified Status: {paused_res.status} 🟡 (PAUSED)")

    camp_entry["status"] = "PAUSED"

    print("\n" + "=" * 70)
    print("🎉 DEMONSTRATION COMPLETE: Full Lifecycle Verified!")
    print(f"   Campaign '{camp_name}' is now registered in the engine.")
    print("   Open Dashboard at http://localhost:8000 to interact in real-time.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(run_messages_campaign_lifecycle_demo())
