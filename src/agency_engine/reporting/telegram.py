"""Telegram messaging service with MarkdownV2 escaping and deduplication."""

from __future__ import annotations

import re

import httpx
import structlog

logger = structlog.get_logger()

# Characters that must be escaped in Telegram MarkdownV2
MARKDOWN_V2_CHARS = r"_*[]()~`>#+-=|{}.!\\"
ESCAPE_RE = re.compile(f"([{re.escape(MARKDOWN_V2_CHARS)}])")


def escape_markdown_v2(text: str) -> str:
    """Escape special characters required by Telegram MarkdownV2."""
    return ESCAPE_RE.sub(r"\\\1", text)


class TelegramNotifier:
    """Dispatches deduplicated, sanitized briefing reports to Telegram."""

    def __init__(
        self,
        bot_token: str | None = None,
        default_chat_id: str | None = None,
        dry_run: bool = False,
    ) -> None:
        self.bot_token = bot_token
        self.default_chat_id = default_chat_id
        self.dry_run = dry_run or not bool(bot_token)
        self._sent_keys: set[str] = set()

    async def send_message(
        self,
        text: str,
        chat_id: str | None = None,
        dedup_key: str | None = None,
    ) -> bool:
        target_chat = chat_id or self.default_chat_id
        if not target_chat:
            logger.warning("telegram_chat_id_missing", text_preview=text[:100])
            return False

        if dedup_key:
            if dedup_key in self._sent_keys:
                logger.info("telegram_duplicate_message_skipped", dedup_key=dedup_key)
                return True
            self._sent_keys.add(dedup_key)

        if self.dry_run or not self.bot_token:
            logger.info("telegram_dry_run_dispatch", chat_id=target_chat, text=text[:200])
            return True

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        # Telegram limit is 4096 characters per message
        chunks = [text[i : i + 4000] for i in range(0, len(text), 4000)]

        async with httpx.AsyncClient(timeout=15.0) as client:
            for chunk in chunks:
                payload = {
                    "chat_id": target_chat,
                    "text": chunk,
                    "parse_mode": "MarkdownV2",
                    "disable_web_page_preview": True,
                }
                try:
                    resp = await client.post(url, json=payload)
                    resp.raise_for_status()
                except Exception as exc:
                    logger.error("telegram_send_failed", error=str(exc))
                    return False

        return True
