"""Rollback engine for reversing executed changes."""

from __future__ import annotations

import uuid

import structlog

from agency_engine.domain.enums import ActionState, ActionType
from agency_engine.domain.models import ActionProposal, ExecutionRecord
from agency_engine.platforms.base import AdsPlatform

logger = structlog.get_logger()


class RollbackEngine:
    """Restores pre-execution resource states in case of anomalies or human override."""

    async def rollback(
        self,
        execution_record: ExecutionRecord,
        original_proposal: ActionProposal,
        platform_adapter: AdsPlatform,
    ) -> bool:
        if not execution_record.rollback_supported or execution_record.rolled_back:
            logger.warning(
                "rollback_not_possible",
                execution_id=execution_record.execution_id,
                action_id=execution_record.action_id,
            )
            return False

        # Build compensating proposal
        reverse_action = original_proposal.action
        if original_proposal.action == ActionType.PAUSE:
            reverse_action = ActionType.ENABLE
        elif original_proposal.action == ActionType.ENABLE:
            reverse_action = ActionType.PAUSE

        compensating_proposal = ActionProposal(
            action_id=f"rb_{uuid.uuid4().hex[:10]}",
            fingerprint=f"rb_fp_{execution_record.fingerprint}",
            client_slug=original_proposal.client_slug,
            platform=original_proposal.platform,
            action=reverse_action,
            resource_id=original_proposal.resource_id,
            resource_name=original_proposal.resource_name,
            old_value=execution_record.post_state_value,
            new_value=execution_record.pre_state_value,
            reason=f"Rollback of execution {execution_record.execution_id}",
            confidence=1.0,
            requires_approval=False,
        )

        try:
            await platform_adapter.execute_action(
                proposal=compensating_proposal,
                idempotency_key=f"rollback_key_{execution_record.execution_id}",
            )
            execution_record.rolled_back = True
            execution_record.state = ActionState.ROLLED_BACK
            logger.info("rollback_executed_successfully", execution_id=execution_record.execution_id)
            return True
        except Exception as exc:
            logger.exception("rollback_failed", execution_id=execution_record.execution_id, error=str(exc))
            return False
