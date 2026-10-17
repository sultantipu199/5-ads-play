import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

export type VerticalReelAdProps = {
  brandName?: string;
  headline?: string;
  discountText?: string;
  productTitle?: string;
  features?: string[];
  ctaText?: string;
  primaryColor?: string;
  accentColor?: string;
};

export const VerticalReelAd: React.FC<VerticalReelAdProps> = ({
  brandName = "B-FASHION EXPLORE",
  headline = "🔥 VIP COLLECTION DROP",
  discountText = "FLAT 20% OFF",
  productTitle = "Luxury Drop-Shoulder Streetwear",
  features = [
    "✨ 100% Combed Premium Cotton",
    "🚀 Nationwide Cash on Delivery",
    "💬 Instant Chat Order on Messenger & IG",
  ],
  ctaText = "💬 Send Message to Claim 20% Off",
  primaryColor = "#0F172A",
  accentColor = "#F59E0B",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Animations using Remotion spring physics
  const introScale = spring({
    frame,
    fps,
    config: { damping: 12, mass: 0.5 },
  });

  const badgeTranslate = interpolate(frame, [15, 45], [-80, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const ctaPulse = interpolate(
    Math.sin((frame / fps) * 4),
    [-1, 1],
    [0.96, 1.04]
  );

  return (
    <AbsoluteFill
      style={{
        backgroundColor: primaryColor,
        fontFamily: "'Outfit', 'Inter', sans-serif",
        color: "#ffffff",
        padding: "80px 60px",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        boxSizing: "border-box",
        overflow: "hidden",
      }}
    >
      {/* Background Decorative Ambient Glows */}
      <div
        style={{
          position: "absolute",
          top: "-150px",
          right: "-150px",
          width: "550px",
          height: "550px",
          borderRadius: "50%",
          background: `radial-gradient(circle, ${accentColor}44 0%, transparent 70%)`,
          filter: "blur(70px)",
          pointerEvents: "none",
        }}
      />
      <div
        style={{
          position: "absolute",
          bottom: "100px",
          left: "-150px",
          width: "600px",
          height: "600px",
          borderRadius: "50%",
          background: "radial-gradient(circle, #10B98133 0%, transparent 70%)",
          filter: "blur(80px)",
          pointerEvents: "none",
        }}
      />

      {/* Top Header & Brand Bar */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          zIndex: 10,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <div
            style={{
              width: "56px",
              height: "56px",
              borderRadius: "16px",
              background: `linear-gradient(135deg, ${accentColor}, #10B981)`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontWeight: 800,
              fontSize: "28px",
              color: "#0F172A",
            }}
          >
            B
          </div>
          <div>
            <div
              style={{
                fontSize: "26px",
                fontWeight: 800,
                letterSpacing: "3px",
                color: "#f8fafc",
              }}
            >
              {brandName}
            </div>
            <div
              style={{
                fontSize: "18px",
                color: "#94a3b8",
                letterSpacing: "1px",
              }}
            >
              VERIFIED FASHION BOUTIQUE
            </div>
          </div>
        </div>

        {/* Animated Discount Pill Badge */}
        <div
          style={{
            background: accentColor,
            color: "#0F172A",
            padding: "12px 28px",
            borderRadius: "40px",
            fontWeight: 800,
            fontSize: "22px",
            letterSpacing: "1px",
            transform: `translateY(${badgeTranslate}px)`,
            boxShadow: `0 10px 25px ${accentColor}55`,
          }}
        >
          {discountText}
        </div>
      </div>

      {/* Center Motion Showcase */}
      <div
        style={{
          zIndex: 10,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          textAlign: "center",
          margin: "auto 0",
        }}
      >
        <div
          style={{
            fontSize: "36px",
            fontWeight: 700,
            color: accentColor,
            letterSpacing: "2px",
            marginBottom: "16px",
            textTransform: "uppercase",
          }}
        >
          {headline}
        </div>

        <div
          style={{
            fontSize: "64px",
            fontWeight: 900,
            lineHeight: 1.15,
            marginBottom: "36px",
            transform: `scale(${introScale})`,
            maxWidth: "920px",
            background: "linear-gradient(180deg, #FFFFFF 30%, #CBD5E1 100%)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
          }}
        >
          {productTitle}
        </div>

        {/* Feature Cards List */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "20px",
            width: "100%",
            maxWidth: "840px",
          }}
        >
          {features.map((feat, idx) => {
            const featEntrance = spring({
              frame: frame - (40 + idx * 20),
              fps,
              config: { damping: 14 },
            });
            return (
              <div
                key={idx}
                style={{
                  background: "rgba(255, 255, 255, 0.07)",
                  backdropFilter: "blur(12px)",
                  border: "1px solid rgba(255, 255, 255, 0.15)",
                  borderRadius: "20px",
                  padding: "24px 32px",
                  fontSize: "30px",
                  fontWeight: 600,
                  color: "#f1f5f9",
                  textAlign: "left",
                  transform: `translateX(${(1 - featEntrance) * 120}px)`,
                  opacity: featEntrance,
                }}
              >
                {feat}
              </div>
            );
          })}
        </div>
      </div>

      {/* Bottom CTA Bar */}
      <div
        style={{
          zIndex: 10,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: "18px",
        }}
      >
        <div
          style={{
            width: "100%",
            background: `linear-gradient(135deg, ${accentColor}, #10B981)`,
            color: "#0F172A",
            padding: "30px 40px",
            borderRadius: "28px",
            fontWeight: 800,
            fontSize: "34px",
            textAlign: "center",
            transform: `scale(${ctaPulse})`,
            boxShadow: `0 20px 50px ${accentColor}66`,
            letterSpacing: "0.5px",
          }}
        >
          {ctaText}
        </div>
        <div
          style={{
            fontSize: "20px",
            color: "#94a3b8",
            letterSpacing: "1px",
          }}
        >
          Advantage+ Placement • Facebook Messenger &amp; Instagram Direct
        </div>
      </div>
    </AbsoluteFill>
  );
};
