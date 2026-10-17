"""Real-time briefing generator based strictly on normalized snapshot data."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from agency_engine.domain.models import ActionProposal, CanonicalMetric
from agency_engine.reporting.telegram import TelegramNotifier, escape_markdown_v2


class BriefingService:
    """Compiles client executive briefings without synthetic or hardcoded metrics."""

    def __init__(self, notifier: TelegramNotifier | None = None) -> None:
        self.notifier = notifier or TelegramNotifier()

    def generate_briefing_text(
        self,
        client_name: str,
        metrics: list[CanonicalMetric],
        proposals: list[ActionProposal] | None = None,
        stale_threshold_minutes: int = 180,
    ) -> str:
        now = datetime.now(UTC)
        proposals = proposals or []

        if not metrics:
            return (
                f"📊 *{escape_markdown_v2(client_name)} Daily Executive Briefing*\n"
                f"⚠️ *DATA UNAVAILABLE*: No synchronized metrics available in repository\\.\n"
                f"Generated at: `{escape_markdown_v2(now.strftime('%Y-%m-%d %H:%M UTC'))}`\n"
            )

        # Calculate aggregates
        total_spend = Decimal("0.0")
        total_conversions = Decimal("0.0")
        max_freshness = max(m.data_freshness_minutes for m in metrics)
        currency = metrics[0].reporting_currency

        platform_breakdown: dict[str, dict[str, Any]] = {}

        for m in metrics:
            total_spend += m.converted_spend
            total_conversions += m.conversions
            p = m.platform.value
            if p not in platform_breakdown:
                platform_breakdown[p] = {
                    "spend": Decimal("0.0"),
                    "conversions": Decimal("0.0"),
                    "campaigns": 0,
                }
            platform_breakdown[p]["spend"] += m.converted_spend
            platform_breakdown[p]["conversions"] += m.conversions
            platform_breakdown[p]["campaigns"] += 1

        overall_cpa_str = f"{(total_spend / total_conversions):.2f}" if total_conversions > 0 else "N/A"

        stale_banner = ""
        if max_freshness > stale_threshold_minutes:
            stale_banner = f"⚠️ *STALE DATA WARNING*: Metrics last synchronized {max_freshness} mins ago\\.\n\n"

        lines = [
            f"📊 *{escape_markdown_v2(client_name)} Daily Executive Briefing*",
            stale_banner,
            f"• *Total Daily Spend*: `{escape_markdown_v2(f'{total_spend:.2f} {currency}')}`",
            f"• *Total Conversions*: `{escape_markdown_v2(f'{total_conversions:.0f}')}`",
            f"• *Blended CPA*: `{escape_markdown_v2(f'{overall_cpa_str} {currency}')}`",
            f"• *Data Freshness*: `{escape_markdown_v2(f'{max_freshness} min(s) ago')}`",
            "\n*Platform Breakdown:*",
        ]

        for p_name, data in platform_breakdown.items():
            p_spend = data["spend"]
            p_conv = data["conversions"]
            p_cpa = f"{(p_spend / p_conv):.2f}" if p_conv > 0 else "N/A"
            lines.append(
                f"  ▪ *{escape_markdown_v2(p_name.title())}*: Spend `{escape_markdown_v2(f'{p_spend:.2f} {currency}')}` \\| "
                f"Conv `{escape_markdown_v2(f'{p_conv:.0f}')}` \\| "
                f"CPA `{escape_markdown_v2(p_cpa)}`"
            )

        if proposals:
            lines.append("\n*Proposed Actionable Optimizations:*")
            for prop in proposals:
                lines.append(
                    f"  ▫ *{escape_markdown_v2(prop.action.value)}* on `{escape_markdown_v2(prop.resource_name)}`\n"
                    f"    Reason: _{escape_markdown_v2(prop.reason)}_\n"
                    f"    Action ID: `{escape_markdown_v2(prop.action_id)}`\n"
                    f"    Fingerprint: `{escape_markdown_v2(prop.fingerprint[:12])}`"
                )
        else:
            lines.append("\n*Action Status:* No campaign interventions required \\(All performing within bounds\\)\\.")

        lines.append(f"\n_Generated autonomously at {escape_markdown_v2(now.strftime('%Y-%m-%d %H:%M UTC'))}_")
        return "\n".join(lines)

    async def deliver_briefing(
        self,
        client_name: str,
        client_slug: str,
        metrics: list[CanonicalMetric],
        proposals: list[ActionProposal] | None = None,
        chat_id: str | None = None,
    ) -> bool:
        text = self.generate_briefing_text(client_name, metrics, proposals)
        today_str = datetime.now(UTC).strftime("%Y-%m-%d")
        dedup_key = f"briefing:{client_slug}:{today_str}"
        return await self.notifier.send_message(text=text, chat_id=chat_id, dedup_key=dedup_key)
