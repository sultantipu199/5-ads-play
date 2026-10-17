"""Omnichannel Autonomous Agency Engine - Publish 4 Ads to Meta Ads Manager.

This script takes the 4 pre-created Meta AdSets and 4 Meta AdCreatives for
Tipu Sultan - AI & Data Growth Architect (Page ID: 105656909238175) and
publishes the live Ad entities under Ad Account act_2665580250239749.
"""

import json
import os
import re
import sys

import httpx

ACT_ID = "act_2665580250239749"
PAGE_ID = "105656909238175"
PAGE_NAME = "Tipu Sultan - AI & Data Growth Architect"

ADS_CONFIG = [
    {
        "name": "Ad 1: Text-Only Direct Messaging (AI Growth & Analytics)",
        "adset_id": "120254903760540536",
        "creative_id": "4579539412329267",
        "modality": "TEXT_ONLY",
        "description": "Direct conversation starter focusing on Web Analytics & CAPI consultation",
    },
    {
        "name": "Ad 2: Single Studio Image (AI & Data Growth Architect)",
        "adset_id": "120254903761000536",
        "creative_id": "1887099109119697",
        "modality": "SINGLE_IMAGE",
        "description": "High-impact single visual highlighting Server-Side Tracking & GTM",
    },
    {
        "name": "Ad 3: Multi-Card Carousel (CAPI, GTM & Value Bidding)",
        "adset_id": "120254903761780536",
        "creative_id": "1117140314197725",
        "modality": "CAROUSEL",
        "description": "3-Card Growth Stack carousel showcasing CAPI, Analytics & Value Bidding",
    },
    {
        "name": "Ad 4: Remotion Motion Graphics (9:16 Growth Reel)",
        "adset_id": "120254903762520536",
        "creative_id": "1181501077872193",
        "modality": "REMOTION_VIDEO",
        "description": "Programmatic 9:16 vertical motion graphics reel for Reels & Stories",
    },
]


def get_token() -> str:
    token = os.environ.get("AGENCY_B_FASHION_EXPLORE_META", "")
    if not token and os.path.exists(".env"):
        with open(".env", encoding="utf-8") as f:
            for line in f:
                m = re.match(r"^AGENCY_B_FASHION_EXPLORE_META=(.*)$", line.strip())
                if m:
                    token = m.group(1).strip()
                    break
    return token


def publish_ads(token: str | None = None) -> dict[str, str | int]:
    if not token:
        token = get_token()
    if not token:
        print("❌ Error: Meta Access Token not found in .env or environment.")
        return {"error": "no_token"}

    print("=" * 70)
    print("🚀 Publishing 4 Ads to Meta Ads Manager for Tipu Sultan")
    print(f"Ad Account: {ACT_ID}")
    print(f"Target Facebook Page: {PAGE_NAME} (ID: {PAGE_ID})")
    print("=" * 70)

    results = []
    has_billing_error = False

    for item in ADS_CONFIG:
        print(f"\nPublishing [{item['name']}]...")
        print(f"  AdSet ID: {item['adset_id']}")
        print(f"  Creative ID: {item['creative_id']}")
        payload = {
            "name": item["name"],
            "adset_id": item["adset_id"],
            "creative": json.dumps({"creative_id": item["creative_id"]}),
            "status": "PAUSED",
            "access_token": token,
        }
        try:
            r = httpx.post(f"https://graph.facebook.com/v19.0/{ACT_ID}/ads", data=payload, timeout=20.0)
            res = r.json()
            if r.status_code == 200 and "id" in res:
                print(f"  ✅ SUCCESS: Ad published on Meta with ID: {res['id']}")
                results.append({"name": item["name"], "id": res["id"], "status": "LIVE_ON_META"})
            else:
                err = res.get("error", {})
                err_code = err.get("code")
                err_subcode = err.get("error_subcode")
                err_title = err.get("error_user_title", "Unknown")
                err_msg = err.get("error_user_msg", err.get("message"))
                print(f"  ❌ Meta Error (Code {err_code}, Subcode {err_subcode}): {err_title}")
                print(f"     Details: {err_msg}")
                if err_subcode == 1359188 or "Payment Method" in str(err):
                    has_billing_error = True
                results.append({
                    "name": item["name"],
                    "status": "BLOCKED_BY_META",
                    "error_subcode": err_subcode,
                    "error_title": err_title,
                    "error_msg": err_msg,
                })
        except Exception as e:
            print(f"  ❌ Request exception: {e}")

    print("\n" + "=" * 70)
    print("📊 Summary of 4 Ads Publishing Attempt:")
    for r in results:
        print(f" - {r['name']}: {r['status']}")
    print("=" * 70)

    if has_billing_error:
        print("\n⚠️ NOTE: Meta requires an active payment method on act_2665580250239749.")
        print("Add a payment method here: https://adsmanager.facebook.com/adsmanager/billing?act=2665580250239749")

    return {"results": results, "has_billing_error": has_billing_error}


if __name__ == "__main__":
    t = sys.argv[1] if len(sys.argv) > 1 else None
    publish_ads(t)
