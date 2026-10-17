"""Core domain models and canonical schemas."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from agency_engine.domain.enums import (
    ActionState,
    ActionType,
    PlatformName,
    RiskLevel,
)


class Evidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    platform: str
    account_id: str
    resource_id: str | None = None
    metric_name: str
    observed_value: Decimal | str | float
    trace_id: str | None = None
    observed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RawSnapshot(BaseModel):
    snapshot_id: str
    client_slug: str
    platform: PlatformName
    account_id: str
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    raw_payload: dict[str, Any]
    trace_id: str


class CanonicalMetric(BaseModel):
    client_slug: str
    platform: PlatformName
    account_id: str
    campaign_id: str
    campaign_name: str
    local_date: str
    timezone: str
    spend: Decimal = Field(default=Decimal("0.0"))
    impressions: int = Field(default=0, ge=0)
    clicks: int = Field(default=0, ge=0)
    conversions: Decimal = Field(default=Decimal("0.0"), ge=0)
    conversion_type: str = "standard_purchase"
    attribution_window: str = "7d_click_1d_view"
    original_currency: str = "USD"
    reporting_currency: str = "USD"
    fx_rate: Decimal = Field(default=Decimal("1.0"), gt=0)
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    data_freshness_minutes: int = Field(default=0, ge=0)
    trace_id: str

    @property
    def converted_spend(self) -> Decimal:
        return self.spend * self.fx_rate

    @property
    def cpa(self) -> Decimal | None:
        if self.conversions > 0:
            return self.converted_spend / self.conversions
        return None

    @property
    def ctr(self) -> float:
        if self.impressions > 0:
            return (self.clicks / self.impressions) * 100.0
        return 0.0


class PlatformResource(BaseModel):
    platform: PlatformName
    account_id: str
    resource_id: str
    name: str
    status: str
    daily_budget: Decimal | None = None
    currency: str = "USD"
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ActionProposal(BaseModel):
    action_id: str
    fingerprint: str
    client_slug: str
    platform: PlatformName
    action: ActionType
    resource_id: str
    resource_name: str
    old_value: Decimal | str | None = None
    new_value: Decimal | str | None = None
    currency: str = "USD"
    reason: str = Field(default="Automated recommendation")
    evidence: list[Evidence] = Field(default_factory=list)

    confidence: float = Field(ge=0.0, le=1.0)
    risk: RiskLevel = RiskLevel.LOW
    requires_approval: bool = True
    state: ActionState = ActionState.PROPOSED
    proposed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ApprovalRecord(BaseModel):
    action_id: str
    approver: str
    channel: str  # e.g. "cli", "telegram"
    approved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    notes: str | None = None


class ExecutionRecord(BaseModel):
    execution_id: str
    action_id: str
    fingerprint: str
    platform: PlatformName
    state: ActionState
    pre_state_value: Decimal | str | None = None
    post_state_value: Decimal | str | None = None
    executed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    error_message: str | None = None
    rollback_supported: bool = True
    rolled_back: bool = False


class AuditEvent(BaseModel):
    event_id: str
    event_type: str
    client_slug: str
    platform: PlatformName | None = None
    payload: dict[str, Any]
    actor: str = "system"
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
