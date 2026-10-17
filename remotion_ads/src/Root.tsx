import React from "react";
import { Composition } from "remotion";
import { VerticalReelAd, VerticalReelAdProps } from "./VerticalReelAd";
import { SquareFeedAd, SquareFeedAdProps } from "./SquareFeedAd";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="VerticalReelAd"
        component={VerticalReelAd}
        durationInFrames={300}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{
          brandName: "B-FASHION EXPLORE",
          headline: "🔥 VIP COLLECTION DROP",
          discountText: "FLAT 20% OFF",
          productTitle: "Luxury Drop-Shoulder Streetwear",
          features: [
            "✨ 100% Combed Premium Cotton",
            "🚀 Nationwide Cash on Delivery",
            "💬 Instant Chat Order on Messenger & IG",
          ],
          ctaText: "💬 Send Message to Claim 20% Off",
          primaryColor: "#0F172A",
          accentColor: "#F59E0B",
        } satisfies VerticalReelAdProps}
      />

      <Composition
        id="SquareFeedAd"
        component={SquareFeedAd}
        durationInFrames={240}
        fps={30}
        width={1080}
        height={1080}
        defaultProps={{
          brandName: "B-FASHION EXPLORE",
          headline: "⚡ VIP EXCLUSIVE DROP",
          discountText: "20% OFF",
          productTitle: "Contemporary Streetwear Edit",
          callToAction: "💬 Send Message to Order",
          primaryColor: "#0F172A",
          accentColor: "#F59E0B",
        } satisfies SquareFeedAdProps}
      />
    </>
  );
};
