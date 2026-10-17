"""Autonomous AI Creative Studio: Generates single image, carousel, and video creative packages."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from agency_engine.creative.models import CarouselCard, CreativeAsset, CreativeSource, CreativeType


class AICreativeStudio:
    """Generates high-converting ad creative copy, imagery concepts, and carousel packs."""

    SAMPLE_FASHION_VISUALS = [
        "https://images.unsplash.com/photo-1490481651871-ab68de25d43d?w=1080&q=80",
        "https://images.unsplash.com/photo-1483985988355-763728e1935b?w=1080&q=80",
        "https://images.unsplash.com/photo-1445205170230-053b83016050?w=1080&q=80",
        "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?w=1080&q=80",
    ]

    def generate_carousel_suite(
        self,
        theme: str = "VIP Drop 20% Off",
        language: str = "bn",
        target_placement: str = "ALL",
    ) -> CreativeAsset:
        """Autonomously crafts a multi-card carousel creative tailored for fashion sales & direct messaging."""
        asset_id = f"creative_car_{uuid.uuid4().hex[:8]}"
        now_str = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")

        cards = [
            CarouselCard(
                card_index=1,
                image_url=self.SAMPLE_FASHION_VISUALS[0],
                headline="🔥 নতুন কালেকশন ২০% ছাড়" if language == "bn" else "🔥 New Trend Drop 20% Off",
                description="ইনস্টাগ্রাম ও মেসেঞ্জারে অর্ডার করুন" if language == "bn" else "DM or Messenger to order",
                link_url="https://bfashionexplore.com/collection/men",
                call_to_action="SEND_MESSAGE",
            ),
            CarouselCard(
                card_index=2,
                image_url=self.SAMPLE_FASHION_VISUALS[1],
                headline="✨ প্রিমিয়াম স্ট্রিটওয়্যার" if language == "bn" else "✨ Premium Streetwear Fit",
                description="স্টাইলিশ এক্সক্লুসিভ ডিজাইন" if language == "bn" else "Limited Edition Styles",
                link_url="https://bfashionexplore.com/collection/streetwear",
                call_to_action="SEND_MESSAGE",
            ),
            CarouselCard(
                card_index=3,
                image_url=self.SAMPLE_FASHION_VISUALS[2],
                headline="🛍️ ফ্রি ডেলিভারি অফার" if language == "bn" else "🛍️ Nationwide Fast Shipping",
                description="ইনবক্সে মেসেজ দিয়ে কোড নিন" if language == "bn" else "Message to claim voucher",
                link_url="https://bfashionexplore.com/offers",
                call_to_action="SEND_MESSAGE",
            ),
        ]

        primary_text = (
            "🔥 B-Fashion Explore স্পেশাল ভিআইপি সেল! সরাসরি মেসেঞ্জারে বা ইনস্টাগ্রাম ডিরেক্টে চ্যাট করে আপনার ২০% ডিসকাউন্ট ভাউচার কোডটি সংগ্রহ করুন। সীমিত সময়ের এক্সক্লুসিভ স্টক! 🛍️✨"
            if language == "bn"
            else "🔥 B-Fashion Exclusive VIP Drop! Chat directly with our stylists on Messenger or Instagram Direct to claim your 20% discount voucher. 🛍️✨"
        )

        headline = "চ্যাট করুন এবং ২০% ছাড় পান 💬" if language == "bn" else "Chat with Stylist & Get 20% Off 💬"

        return CreativeAsset(
            asset_id=asset_id,
            name=f"B-Fashion {theme} (AI Carousel Suite)",
            creative_type=CreativeType.CAROUSEL,
            source=CreativeSource.AI_GENERATED,
            primary_text=primary_text,
            headline=headline,
            description="Facebook Messenger + Instagram Direct Ordering",
            call_to_action="SEND_MESSAGE",
            media_url=self.SAMPLE_FASHION_VISUALS[0],
            carousel_cards=cards,
            target_placement=target_placement,
            created_at=now_str,
            metadata={"theme": theme, "card_count": len(cards), "language": language},
        )

    def generate_single_image_ad(
        self,
        theme: str = "Summer Trend",
        language: str = "bn",
        target_placement: str = "ALL",
    ) -> CreativeAsset:
        """Autonomously crafts a high-impact single image ad creative."""
        asset_id = f"creative_img_{uuid.uuid4().hex[:8]}"
        now_str = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")

        primary_text = (
            "🌟 ট্রেন্ডি ফ্যাশনে আনুন নতুন লুক! B-Fashion Explore-এর লেটেস্ট ড্রপ এখন লাইভ। অর্ডার করতে ও সাইজ পরামর্শ পেতে এখনই মেসেজ দিন। 💬🛍️"
            if language == "bn"
            else "🌟 Upgrade your style with B-Fashion Explore's latest arrival! Tap below to chat directly with our stylists on Messenger & IG Direct. 💬🛍️"
        )

        return CreativeAsset(
            asset_id=asset_id,
            name=f"B-Fashion {theme} (AI Single Image)",
            creative_type=CreativeType.SINGLE_IMAGE,
            source=CreativeSource.AI_GENERATED,
            primary_text=primary_text,
            headline="ইনবক্সে মেসেজ পাঠান 💬" if language == "bn" else "Send Message to Order 💬",
            description="Advantage+ Placements: Facebook & Instagram",
            call_to_action="SEND_MESSAGE",
            media_url=self.SAMPLE_FASHION_VISUALS[1],
            target_placement=target_placement,
            created_at=now_str,
            metadata={"theme": theme, "aspect_ratio": "1:1", "language": language},
        )
