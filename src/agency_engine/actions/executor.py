"""Safe action executor with pre-state verification and audit generation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog

from agency_engine.actions.idempotency import IdempotencyRegistry
from agency_engine.domain.enums import ActionState, ActionType
from agency_engine.domain.exceptions import StateConflictError
from agency_engine.domain.models import ActionProposal, ExecutionRecord
from agency_engine.platforms.base import AdsPlatform

logger = structlog.get_logger()


class ActionExecutor:
    """Safely executes mutating changes on advertising platforms."""

    def __init__(self, idempotency_registry: IdempotencyRegistry | None = None) -> None:
        self.idempotency = idempotency_registry or IdempotencyRegistry()

    async def execute(
        self,
        proposal: ActionProposal,
        platform_adapter: AdsPlatform,
        account_id: str,
    ) -> ExecutionRecord:
        execution_id = f"exec_{uuid.uuid4().hex[:10]}"

        # 1. Register idempotency fingerprint
        fingerprint = self.idempotency.check_and_register(proposal)

        # 2. Pre-execution live state re-reading
        live_resource = await platform_adapter.get_resource(
            account_id=account_id,
            resource_id=proposal.resource_id,
        )
        if not live_resource:
            raise StateConflictError(f"Resource {proposal.resource_id} not found upstream prior to execution.")

        current_state_val = (
            str(live_resource.daily_budget) if proposal.action == ActionType.UPDATE_BUDGET else live_resource.status
        )

        if proposal.old_value is not None and str(proposal.old_value) != current_state_val:
            raise StateConflictError(
                f"Upstream resource state changed! Expected '{proposal.old_value}' but found '{current_state_val}'."
            )

        # 3. Platform mutation
        try:
            await platform_adapter.execute_action(
                proposal=proposal,
                idempotency_key=fingerprint,
            )

            # 4. Post-execution verification
            post_live_res = await platform_adapter.get_resource(
                account_id=account_id,
                resource_id=proposal.resource_id,
            )
            post_state_val = (
                str(post_live_res.daily_budget)
                if post_live_res and proposal.action == ActionType.UPDATE_BUDGET
                else (post_live_res.status if post_live_res else None)
            )

            record = ExecutionRecord(
                execution_id=execution_id,
                action_id=proposal.action_id,
                fingerprint=fingerprint,
                platform=proposal.platform,
                state=ActionState.EXECUTED,
                pre_state_value=current_state_val,
                post_state_value=post_state_val,
                executed_at=datetime.now(UTC),
                rollback_supported=True,
                rolled_back=False,
            )
            logger.info(
                "action_successfully_executed",
                action_id=proposal.action_id,
                platform=proposal.platform.value,
                resource_id=proposal.resource_id,
                pre_value=current_state_val,
                post_value=post_state_val,
            )
            return record

        except Exception as exc:
            logger.exception(
                "action_execution_failed",
                action_id=proposal.action_id,
                error=str(exc),
            )
            return ExecutionRecord(
                execution_id=execution_id,
                action_id=proposal.action_id,
                fingerprint=fingerprint,
                platform=proposal.platform,
                state=ActionState.FAILED,
                pre_state_value=current_state_val,
                post_state_value=None,
                executed_at=datetime.now(UTC),
                error_message=str(exc),
                rollback_supported=False,
                rolled_back=False,
            )
