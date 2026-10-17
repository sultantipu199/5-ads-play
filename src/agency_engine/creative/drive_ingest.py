"""Google Drive & Local File Asset Ingestion Pipeline."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agency_engine.creative.models import CarouselCard, CreativeAsset, CreativeSource, CreativeType


class DriveAssetIngestor:
    """Manages intake of manual creatives from Google Drive or local file drops."""

    def __init__(self, upload_dir: Path | None = None) -> None:
        self.upload_dir = upload_dir or (Path(__file__).resolve().parent.parent.parent.parent / "assets" / "uploads")
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def ingest_from_drive_link(
        self,
        drive_url: str,
        name: str = "Google Drive Asset Drop",
        creative_type: CreativeType = CreativeType.CAROUSEL,
        primary_text: str = "",
        headline: str = "",
        target_placement: str = "ALL",
        custom_cards: list[dict[str, Any]] | None = None,
    ) -> CreativeAsset:
        """Parses a Google Drive folder/file link and creates an active creative asset."""
        asset_id = f"creative_drv_{uuid.uuid4().hex[:8]}"
        now_str = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")

        cards: list[CarouselCard] = []
        if custom_cards:
            for i, c in enumerate(custom_cards, 1):
                cards.append(
                    CarouselCard(
                        card_index=i,
                        image_url=c.get("image_url", "https://images.unsplash.com/photo-1490481651871-ab68de25d43d?w=1080"),
                        headline=c.get("headline", f"Card {i} Headline"),
                        description=c.get("description", "Direct Order"),
                        link_url=c.get("link_url", "https://bfashionexplore.com"),
                        call_to_action=c.get("call_to_action", "SEND_MESSAGE"),
                    )
                )

        p_text = (
            primary_text
            or "🔥 B-Fashion Explore New Arrival! Chat with us directly on Messenger or Instagram Direct to order. 🛍️✨"
        )
        h_line = headline or "Chat with Us & Get Exclusive Offers 💬"

        return CreativeAsset(
            asset_id=asset_id,
            name=name,
            creative_type=creative_type,
            source=CreativeSource.MANUAL_DRIVE_UPLOAD,
            primary_text=p_text,
            headline=h_line,
            description="Imported from Google Drive",
            call_to_action="SEND_MESSAGE",
            media_url=cards[0].image_url if cards else "https://images.unsplash.com/photo-1490481651871-ab68de25d43d?w=1080",
            carousel_cards=cards,
            drive_link=drive_url,
            target_placement=target_placement,
            created_at=now_str,
            metadata={"drive_url": drive_url, "imported_files": len(cards) or 1},
        )

    def scan_local_folder(self) -> list[str]:
        """Scans local assets/uploads directory for uploaded media files."""
        if not self.upload_dir.exists():
            return []
        valid_exts = {".jpg", ".jpeg", ".png", ".webp", ".mp4"}
        return [f.name for f in self.upload_dir.iterdir() if f.suffix.lower() in valid_exts]
