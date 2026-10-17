"""Integration tests for action execution, idempotency, and rollback."""

from decimal import Decimal

import pytest

from agency_engine.actions.executor import ActionExecutor
from agency_engine.actions.idempotency import IdempotencyRegistry
from agency_engine.actions.rollback import RollbackEngine
from agency_engine.domain.enums import ActionState, ActionType, PlatformName
from agency_engine.domain.exceptions import IdempotencyConflictError, StateConflictError
from agency_engine.domain.models import ActionProposal
from agency_engine.platforms.fakes import FakePlatformAdapter


@pytest.mark.asyncio
async def test_idempotent_execution_and_duplicate_prevention() -> None:
    adapter = FakePlatformAdapter(PlatformName.META)
    registry = IdempotencyRegistry()
    executor = ActionExecutor(idempotency_registry=registry)

    proposal = ActionProposal(
        action_id="act_test_idem",
        fingerprint="fp_unique_123",
        client_slug="global_brand",
        platform=PlatformName.META,
        action=ActionType.PAUSE,
        resource_id="camp_101",
        resource_name="Meta Campaign 101",
        old_value="ACTIVE",
        new_value="PAUSED",
        confidence=0.95,
    )

    # First execution succeeds
    record = await executor.execute(proposal, adapter, "acc_default")
    assert record.state == ActionState.EXECUTED
    assert record.pre_state_value == "ACTIVE"
    assert record.post_state_value == "PAUSED"

    # Second execution must be blocked by idempotency
    with pytest.raises(IdempotencyConflictError):
        await executor.execute(proposal, adapter, "acc_default")


@pytest.mark.asyncio
async def test_state_conflict_detection() -> None:
    adapter = FakePlatformAdapter(PlatformName.META)
    executor = ActionExecutor()

    # Proposal expects old_value to be ACTIVE, but let's change it upstream
    camp = await adapter.get_resource("acc_default", "camp_101")
    assert camp is not None
    camp.status = "PAUSED"

    proposal = ActionProposal(
        action_id="act_conflict",
        fingerprint="fp_conflict_456",
        client_slug="global_brand",
        platform=PlatformName.META,
        action=ActionType.PAUSE,
        resource_id="camp_101",
        resource_name="Camp 101",
        old_value="ACTIVE",  # Conflict! Upstream is already PAUSED
        new_value="PAUSED",
        confidence=0.9,
    )

    with pytest.raises(StateConflictError):
        await executor.execute(proposal, adapter, "acc_default")


@pytest.mark.asyncio
async def test_rollback_engine() -> None:
    adapter = FakePlatformAdapter(PlatformName.META)
    executor = ActionExecutor()
    rollback_engine = RollbackEngine()

    proposal = ActionProposal(
        action_id="act_rb",
        fingerprint="fp_rb_789",
        client_slug="global_brand",
        platform=PlatformName.META,
        action=ActionType.UPDATE_BUDGET,
        resource_id="camp_101",
        resource_name="Camp 101",
        old_value="150.00",
        new_value="165.00",
        confidence=0.95,
    )

    record = await executor.execute(proposal, adapter, "acc_default")
    assert record.state == ActionState.EXECUTED
    # Resource now has budget 165.00
    res = await adapter.get_resource("acc_default", "camp_101")
    assert res is not None and res.daily_budget == Decimal("165.00")

    # Perform Rollback
    success = await rollback_engine.rollback(record, proposal, adapter)
    assert success is True
    # Resource reverted back to 150.00
    res_reverted = await adapter.get_resource("acc_default", "camp_101")
    assert res_reverted is not None and res_reverted.daily_budget == Decimal("150.00")
