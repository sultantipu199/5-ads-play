"""Domain event definitions."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class DomainEvent(BaseModel):
    event_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    client_slug: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class SnapshotIngestedEvent(DomainEvent):
    platform: str
    snapshot_id: str
    trace_id: str


class ProposalGeneratedEvent(DomainEvent):
    action_id: str
    platform: str
    action_type: str
    risk_level: str


class ActionApprovedEvent(DomainEvent):
    action_id: str
    approver: str
    channel: str


class ActionExecutedEvent(DomainEvent):
    action_id: str
    fingerprint: str
    platform: str
    status: str


class CircuitBreakerTriggeredEvent(DomainEvent):
    reason: str
    metric_or_platform: str
