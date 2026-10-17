"""Human-in-the-loop approval management and validation."""

from __future__ import annotations

from datetime import UTC, datetime

import structlog

from agency_engine.domain.models import ActionProposal, ApprovalRecord

logger = structlog.get_logger()


class ApprovalManager:
    """Manages and verifies human approvals from CLI or authorized Telegram operators."""

    def __init__(self, telegram_allowlist: list[str] | None = None) -> None:
        self.telegram_allowlist = set(telegram_allowlist or [])
        self._approvals: dict[str, ApprovalRecord] = {}

    def approve_action(
        self,
        proposal: ActionProposal,
        approver: str,
        channel: str = "cli",
        notes: str | None = None,
    ) -> ApprovalRecord:
        # If approval arrives via Telegram, enforce authorized allowlist
        if channel == "telegram" and self.telegram_allowlist and approver not in self.telegram_allowlist:
            raise PermissionError(f"User {approver} is not authorized to approve actions via Telegram")

        record = ApprovalRecord(
            action_id=proposal.action_id,
            approver=approver,
            channel=channel,
            approved_at=datetime.now(UTC),
            notes=notes,
        )
        self._approvals[proposal.action_id] = record
        logger.info(
            "action_approved_by_operator",
            action_id=proposal.action_id,
            approver=approver,
            channel=channel,
        )
        return record

    def is_approved(self, action_id: str) -> bool:
        return action_id in self._approvals

    def get_approval(self, action_id: str) -> ApprovalRecord | None:
        return self._approvals.get(action_id)
