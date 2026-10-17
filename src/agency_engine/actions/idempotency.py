"""Cryptographic idempotency fingerprinting and duplication prevention."""

from __future__ import annotations

import hashlib
from typing import Any

import structlog

from agency_engine.domain.exceptions import IdempotencyConflictError
from agency_engine.domain.models import ActionProposal

logger = structlog.get_logger()


class IdempotencyRegistry:
    """Tracks executed action fingerprints to prevent duplicate execution across retries."""

    def __init__(self) -> None:
        self._executed_fingerprints: set[str] = set()

    @staticmethod
    def generate_fingerprint(
        client_slug: str,
        platform: str,
        resource_id: str,
        action: str,
        intended_value: Any,
        policy_version: str = "v1.0",
    ) -> str:
        raw_key = f"{client_slug}:{platform}:{resource_id}:{action}:{str(intended_value)}:{policy_version}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def check_and_register(self, proposal: ActionProposal) -> str:
        """Register action fingerprint. Raises IdempotencyConflictError if already executed."""
        fp = proposal.fingerprint or self.generate_fingerprint(
            client_slug=proposal.client_slug,
            platform=proposal.platform.value,
            resource_id=proposal.resource_id,
            action=proposal.action.value,
            intended_value=proposal.new_value,
        )

        if fp in self._executed_fingerprints:
            logger.warning(
                "duplicate_action_blocked",
                action_id=proposal.action_id,
                fingerprint=fp,
                resource_id=proposal.resource_id,
            )
            raise IdempotencyConflictError(
                f"Action with fingerprint {fp} has already been executed. Blocking duplicate mutation."
            )

        self._executed_fingerprints.add(fp)
        return fp

    def is_executed(self, fingerprint: str) -> bool:
        return fingerprint in self._executed_fingerprints
