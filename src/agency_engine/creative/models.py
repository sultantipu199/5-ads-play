"""Domain models for Ad Creatives, Carousel assets, and Drive Ingestion."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class CreativeType(StrEnum):
    SINGLE_IMAGE = "SINGLE_IMAGE"
    CAROUSEL = "CAROUSEL"
    VIDEO = "VIDEO"


class CreativeSource(StrEnum):
    MANUAL_DRIVE_UPLOAD = "MANUAL_DRIVE_UPLOAD"
    AI_GENERATED = "AI_GENERATED"


class CarouselCard(BaseModel):
    card_index: int = 1
    image_url: str
    headline: str
    description: str = ""
    link_url: str = "https://bfashionexplore.com"
    call_to_action: str = "SEND_MESSAGE"


class CreativeAsset(BaseModel):
    asset_id: str
    name: str
    creative_type: CreativeType = CreativeType.SINGLE_IMAGE
    source: CreativeSource = CreativeSource.AI_GENERATED
    primary_text: str
    headline: str
    description: str = ""
    call_to_action: str = "SEND_MESSAGE"
    media_url: str = ""
    carousel_cards: list[CarouselCard] = Field(default_factory=list)
    drive_link: str | None = None
    target_placement: str = "ALL"  # ALL, INSTAGRAM, FACEBOOK
    created_at: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
