"""Remotion Programmatic Video & Motion Graphics Engine.

Integrates Remotion React-based video generation with the Omnichannel Agency Engine,
allowing autonomous generation, preview, and rendering of high-converting Video Ad Creatives
(9:16 Vertical Reels/Stories and 1:1 Square Feed Ads).
"""

from __future__ import annotations

import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agency_engine.creative.models import CreativeAsset, CreativeSource, CreativeType


class RemotionVideoEngine:
    """Manages Remotion compositions, programmatic rendering, and video ad asset packaging."""

    AVAILABLE_COMPOSITIONS = {
        "VerticalReelAd": {
            "name": "9:16 Vertical Reel & Story Video Ad",
            "aspect_ratio": "9:16",
            "dimensions": "1080x1920",
            "fps": 30,
            "duration_frames": 300,
            "duration_seconds": 10.0,
            "target_placements": "Instagram Reels, Instagram Stories, Facebook Stories",
            "preview_image": "/reel-preview.png",
        },
        "SquareFeedAd": {
            "name": "1:1 Square Feed Motion Graphics Ad",
            "aspect_ratio": "1:1",
            "dimensions": "1080x1080",
            "fps": 30,
            "duration_frames": 240,
            "duration_seconds": 8.0,
            "target_placements": "Facebook Feed, Instagram Feed & Explore",
            "preview_image": "/feed-preview.png",
        },
    }

    def __init__(self, remotion_project_dir: Path | None = None) -> None:
        self.project_dir = remotion_project_dir or (Path(__file__).resolve().parent.parent.parent.parent / "remotion_ads")

    def list_compositions(self) -> dict[str, Any]:
        """Returns metadata for all available Remotion ad compositions."""
        return self.AVAILABLE_COMPOSITIONS

    def create_video_ad_asset(
        self,
        composition_id: str = "VerticalReelAd",
        product_title: str = "Luxury Drop-Shoulder Streetwear",
        headline: str = "🔥 VIP COLLECTION DROP",
        discount_text: str = "FLAT 20% OFF",
        cta_text: str = "💬 Send Message to Claim 20% Off",
        language: str = "bn",
        primary_color: str = "#0F172A",
        accent_color: str = "#F59E0B",
    ) -> CreativeAsset:
        """Autonomously packages a Remotion motion graphics video ad creative asset."""
        comp_meta = self.AVAILABLE_COMPOSITIONS.get(composition_id, self.AVAILABLE_COMPOSITIONS["VerticalReelAd"])
        asset_id = f"remotion_vid_{uuid.uuid4().hex[:8]}"
        now_str = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")

        p_text_bn = (
            f"🎬 [{product_title} - মোশন গ্রাফিক্স ড্রপ]\n"
            f"{headline} - বিশেষ {discount_text} ভাউচার পেতে এখনই সরাসরি মেসেঞ্জারে বা ইনস্টাগ্রাম ডিরেক্টে চ্যাট করুন। "
            f"১০০% কটন প্রিমিয়াম ফেব্রিক ও সারাদেশে ক্যাশ অন ডেলিভারি! 🛍️✨"
        )
        p_text_en = (
            f"🎬 [{product_title} - Remotion Video Ad]\n"
            f"{headline} - Claim your {discount_text} exclusive VIP discount voucher! "
            f"Direct message our stylists on Messenger & Instagram to order now. 🛍️✨"
        )

        return CreativeAsset(
            asset_id=asset_id,
            name=f"Remotion {comp_meta['name']} ({product_title})",
            creative_type=CreativeType.VIDEO,
            source=CreativeSource.AI_GENERATED,
            primary_text=p_text_bn if language == "bn" else p_text_en,
            headline=f"{product_title} ({discount_text}) 💬",
            description=f"Remotion React Motion Graphics • {comp_meta['aspect_ratio']} • {comp_meta['dimensions']}",
            call_to_action="SEND_MESSAGE",
            media_url=comp_meta["preview_image"],
            target_placement="INSTAGRAM" if comp_meta["aspect_ratio"] == "9:16" else "ALL",
            created_at=now_str,
            metadata={
                "tool": "Remotion",
                "framework": "Remotion (React + TypeScript)",
                "composition_id": composition_id,
                "aspect_ratio": comp_meta["aspect_ratio"],
                "dimensions": comp_meta["dimensions"],
                "fps": comp_meta["fps"],
                "duration_seconds": comp_meta["duration_seconds"],
                "props": {
                    "productTitle": product_title,
                    "headline": headline,
                    "discountText": discount_text,
                    "ctaText": cta_text,
                    "primaryColor": primary_color,
                    "accentColor": accent_color,
                },

            },
        )

    def render_composition(
        self,
        composition_id: str,
        output_filename: str = "video_ad.mp4",
    ) -> dict[str, Any]:
        """Triggers local CLI rendering for a Remotion composition."""
        out_path = self.project_dir / "out" / output_filename
        out_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            "npx",
            "remotion",
            "render",
            composition_id,
            f"out/{output_filename}",
        ]
        proc = subprocess.run(cmd, cwd=str(self.project_dir), capture_output=True, text=True, check=False)
        return {
            "success": proc.returncode == 0,
            "output_file": str(out_path),
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }
