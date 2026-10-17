import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

export type SquareFeedAdProps = {
  brandName?: string;
  headline?: string;
  discountText?: string;
  productTitle?: string;
  callToAction?: string;
  primaryColor?: string;
  accentColor?: string;
};

export const SquareFeedAd: React.FC<SquareFeedAdProps> = ({
  brandName = "B-FASHION EXPLORE",
  headline = "⚡ VIP EXCLUSIVE DROP",
  discountText = "20% OFF",
  productTitle = "Contemporary Streetwear Edit",
  callToAction = "💬 Send Message to Order",
  primaryColor = "#0F172A",
  accentColor = "#F59E0B",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleProgress = spring({
    frame,
    fps,
    config: { damping: 14, mass: 0.6 },
  });

  const buttonPulse = interpolate(
    Math.sin((frame / fps) * 5),
    [-1, 1],
    [0.97, 1.03]
  );

  return (
    <AbsoluteFill
      style={{
        backgroundColor: primaryColor,
        fontFamily: "'Outfit', 'Inter', sans-serif",
        color: "#ffffff",
        padding: "60px",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        boxSizing: "border-box",
        overflow: "hidden",
      }}
    >
      {/* Background Radial Glow */}
      <div
        style={{
          position: "absolute",
          top: "-100px",
          right: "-100px",
          width: "450px",
          height: "450px",
          borderRadius: "50%",
          background: `radial-gradient(circle, ${accentColor}44 0%, transparent 70%)`,
          filter: "blur(60px)",
        }}
      />

      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          zIndex: 10,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
          <div
            style={{
              width: "48px",
              height: "48px",
              borderRadius: "14px",
              background: `linear-gradient(135deg, ${accentColor}, #10B981)`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontWeight: 800,
              fontSize: "24px",
              color: "#0F172A",
            }}
          >
            B
          </div>
          <div style={{ fontSize: "22px", fontWeight: 800, letterSpacing: "2px" }}>
            {brandName}
          </div>
        </div>

        <div
          style={{
            background: accentColor,
            color: "#0F172A",
            padding: "8px 22px",
            borderRadius: "30px",
            fontWeight: 800,
            fontSize: "18px",
          }}
        >
          {discountText}
        </div>
      </div>

      {/* Hero Showcase Center */}
      <div
        style={{
          zIndex: 10,
          textAlign: "center",
          margin: "auto 0",
        }}
      >
        <div
          style={{
            fontSize: "24px",
            fontWeight: 700,
            color: accentColor,
            letterSpacing: "3px",
            marginBottom: "12px",
          }}
        >
          {headline}
        </div>

        <div
          style={{
            fontSize: "52px",
            fontWeight: 900,
            lineHeight: 1.2,
            marginBottom: "24px",
            transform: `scale(${titleProgress})`,
            background: "linear-gradient(180deg, #FFFFFF, #CBD5E1)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
          }}
        >
          {productTitle}
        </div>

        <div
          style={{
            display: "inline-block",
            background: "rgba(255, 255, 255, 0.08)",
            border: "1px solid rgba(255, 255, 255, 0.15)",
            borderRadius: "14px",
            padding: "14px 28px",
            fontSize: "22px",
            color: "#E2E8F0",
          }}
        >
          🚀 100% Cotton &bull; Cash on Delivery &bull; Instant DM Order
        </div>
      </div>

      {/* Bottom CTA */}
      <div
        style={{
          zIndex: 10,
          display: "flex",
          justifyContent: "center",
        }}
      >
        <div
          style={{
            background: `linear-gradient(135deg, ${accentColor}, #10B981)`,
            color: "#0F172A",
            padding: "20px 48px",
            borderRadius: "22px",
            fontWeight: 800,
            fontSize: "26px",
            textAlign: "center",
            transform: `scale(${buttonPulse})`,
            boxShadow: `0 15px 35px ${accentColor}55`,
          }}
        >
          {callToAction}
        </div>
      </div>
    </AbsoluteFill>
  );
};
