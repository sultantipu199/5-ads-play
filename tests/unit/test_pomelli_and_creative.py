"""Unit tests for Google Pomelli, Creative Studio, and Google Drive Ingestion pipelines."""

from __future__ import annotations

from agency_engine.creative.ai_studio import AICreativeStudio
from agency_engine.creative.drive_ingest import DriveAssetIngestor
from agency_engine.creative.models import CreativeSource, CreativeType
from agency_engine.creative.pomelli import BusinessDNA, GooglePomelliEngine, PomelliPhotoshootConfig


def test_business_dna_defaults_and_customization() -> None:
    dna = BusinessDNA()
    assert dna.brand_name == "B-Fashion Explore"
    assert dna.primary_color == "#0F172A"
    assert "Trendy & Youth-Centric" in dna.tone_of_voice
    assert "Streetwear" in dna.keywords


def test_google_pomelli_extract_business_dna() -> None:
    engine = GooglePomelliEngine()
    extracted = engine.extract_business_dna("https://bfashionexplore.com/store")
    assert extracted.brand_name == "B-Fashion Explore"
    assert extracted.website_url == "https://bfashionexplore.com/store"
    assert len(extracted.tone_of_voice) > 0


def test_google_pomelli_generate_campaign_pack() -> None:
    engine = GooglePomelliEngine()
    cfg = PomelliPhotoshootConfig(
        product_name="Winter Streetwear Drop",
        language="bn",
        call_to_action="SEND_MESSAGE",
        discount_rate="20%",
    )
    assets = engine.generate_campaign_pack(cfg)
    assert len(assets) == 3

    # Check 1:1 Carousel pack
    carousel = assets[0]
    assert carousel.creative_type == CreativeType.CAROUSEL
    assert carousel.source == CreativeSource.AI_GENERATED
    assert len(carousel.carousel_cards) == 3
    assert "Google Pomelli" in carousel.metadata["tool"]

    # Check 9:16 Reel / Story format
    reel = assets[1]
    assert reel.creative_type == CreativeType.SINGLE_IMAGE
    assert reel.metadata["aspect_ratio"] == "9:16"

    # Check 1:1 Hero format
    hero = assets[2]
    assert hero.creative_type == CreativeType.SINGLE_IMAGE
    assert hero.metadata["aspect_ratio"] == "1:1"


def test_google_pomelli_prompt_generator() -> None:
    engine = GooglePomelliEngine()
    prompts = engine.generate_pomelli_prompts("Drop-Shoulder Hoodie")
    assert "feed_1x1_studio_photoshoot" in prompts
    assert "reels_9x16_vertical_story" in prompts
    assert "carousel_card_series" in prompts
    assert "Drop-Shoulder Hoodie" in prompts["feed_1x1_studio_photoshoot"]


def test_drive_asset_ingestor_flow() -> None:
    ingestor = DriveAssetIngestor()
    asset = ingestor.ingest_from_drive_link(
        drive_url="https://drive.google.com/drive/folders/1aBcDeFgHiJkLmNoP",
        name="Drive Drop Test",
        creative_type=CreativeType.CAROUSEL,
        primary_text="Custom primary copy from Drive",
        headline="Drive Headline",
    )
    assert asset.source == CreativeSource.MANUAL_DRIVE_UPLOAD
    assert asset.drive_link == "https://drive.google.com/drive/folders/1aBcDeFgHiJkLmNoP"
    assert asset.headline == "Drive Headline"


def test_ai_creative_studio_bilingual_generation() -> None:
    studio = AICreativeStudio()
    car_bn = studio.generate_carousel_suite(language="bn")
    assert "২০%" in car_bn.primary_text

    car_en = studio.generate_carousel_suite(language="en")
    assert "20%" in car_en.primary_text
