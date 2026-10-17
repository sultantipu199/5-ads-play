"""SQLAlchemy persistence models and repository pattern implementations."""

from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from agency_engine.domain.enums import PlatformName
from agency_engine.domain.models import (
    ActionProposal,
    CanonicalMetric,
    ExecutionRecord,
    RawSnapshot,
)
from agency_engine.persistence.database import Base


class RawSnapshotEntity(Base):
    __tablename__ = "raw_snapshots"

    snapshot_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_slug: Mapped[str] = mapped_column(String(64), index=True)
    platform: Mapped[str] = mapped_column(String(32), index=True)
    account_id: Mapped[str] = mapped_column(String(64), index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    raw_payload_json: Mapped[str] = mapped_column(Text)
    trace_id: Mapped[str] = mapped_column(String(64), index=True)


class CanonicalMetricEntity(Base):
    __tablename__ = "canonical_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_slug: Mapped[str] = mapped_column(String(64), index=True)
    platform: Mapped[str] = mapped_column(String(32), index=True)
    account_id: Mapped[str] = mapped_column(String(64), index=True)
    campaign_id: Mapped[str] = mapped_column(String(64), index=True)
    campaign_name: Mapped[str] = mapped_column(String(255))
    local_date: Mapped[str] = mapped_column(String(32), index=True)
    timezone: Mapped[str] = mapped_column(String(64))
    spend: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    impressions: Mapped[int] = mapped_column(Integer)
    clicks: Mapped[int] = mapped_column(Integer)
    conversions: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    conversion_type: Mapped[str] = mapped_column(String(64))
    attribution_window: Mapped[str] = mapped_column(String(64))
    original_currency: Mapped[str] = mapped_column(String(8))
    reporting_currency: Mapped[str] = mapped_column(String(8))
    fx_rate: Mapped[Decimal] = mapped_column(Numeric(10, 4))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    data_freshness_minutes: Mapped[int] = mapped_column(Integer)
    trace_id: Mapped[str] = mapped_column(String(64), index=True)


class ActionProposalEntity(Base):
    __tablename__ = "action_proposals"

    action_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    client_slug: Mapped[str] = mapped_column(String(64), index=True)
    platform: Mapped[str] = mapped_column(String(32))
    action: Mapped[str] = mapped_column(String(32))
    resource_id: Mapped[str] = mapped_column(String(64), index=True)
    resource_name: Mapped[str] = mapped_column(String(255))
    old_value: Mapped[str | None] = mapped_column(String(64), nullable=True)
    new_value: Mapped[str | None] = mapped_column(String(64), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    reason: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    risk: Mapped[str] = mapped_column(String(16))
    state: Mapped[str] = mapped_column(String(32), default="PROPOSED", index=True)
    proposed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class ExecutionRecordEntity(Base):
    __tablename__ = "action_executions"

    execution_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    action_id: Mapped[str] = mapped_column(String(64), ForeignKey("action_proposals.action_id"), index=True)
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    platform: Mapped[str] = mapped_column(String(32))
    state: Mapped[str] = mapped_column(String(32))
    pre_state_value: Mapped[str | None] = mapped_column(String(64), nullable=True)
    post_state_value: Mapped[str | None] = mapped_column(String(64), nullable=True)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    rollback_supported: Mapped[bool] = mapped_column(Boolean, default=True)
    rolled_back: Mapped[bool] = mapped_column(Boolean, default=False)


class AuditEventEntity(Base):
    __tablename__ = "audit_events"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    client_slug: Mapped[str] = mapped_column(String(64), index=True)
    platform: Mapped[str | None] = mapped_column(String(32), nullable=True)
    payload_json: Mapped[str] = mapped_column(Text)
    actor: Mapped[str] = mapped_column(String(64))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class RepositoryManager:
    """Provides high-level async persistence operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save_snapshot(self, snapshot: RawSnapshot) -> None:
        entity = RawSnapshotEntity(
            snapshot_id=snapshot.snapshot_id,
            client_slug=snapshot.client_slug,
            platform=snapshot.platform.value,
            account_id=snapshot.account_id,
            fetched_at=snapshot.fetched_at,
            raw_payload_json=json.dumps(snapshot.raw_payload),
            trace_id=snapshot.trace_id,
        )
        self.session.add(entity)
        await self.session.commit()

    async def save_metrics(self, metrics: list[CanonicalMetric]) -> None:
        for m in metrics:
            entity = CanonicalMetricEntity(
                client_slug=m.client_slug,
                platform=m.platform.value,
                account_id=m.account_id,
                campaign_id=m.campaign_id,
                campaign_name=m.campaign_name,
                local_date=m.local_date,
                timezone=m.timezone,
                spend=m.spend,
                impressions=m.impressions,
                clicks=m.clicks,
                conversions=m.conversions,
                conversion_type=m.conversion_type,
                attribution_window=m.attribution_window,
                original_currency=m.original_currency,
                reporting_currency=m.reporting_currency,
                fx_rate=m.fx_rate,
                fetched_at=m.fetched_at,
                data_freshness_minutes=m.data_freshness_minutes,
                trace_id=m.trace_id,
            )
            self.session.add(entity)
        await self.session.commit()

    async def get_latest_metrics(self, client_slug: str) -> list[CanonicalMetric]:
        stmt = (
            select(CanonicalMetricEntity)
            .where(CanonicalMetricEntity.client_slug == client_slug)
            .order_by(CanonicalMetricEntity.fetched_at.desc())
        )
        res = await self.session.execute(stmt)
        entities = res.scalars().all()
        result = []
        for e in entities:
            result.append(
                CanonicalMetric(
                    client_slug=e.client_slug,
                    platform=PlatformName(e.platform),
                    account_id=e.account_id,
                    campaign_id=e.campaign_id,
                    campaign_name=e.campaign_name,
                    local_date=e.local_date,
                    timezone=e.timezone,
                    spend=e.spend,
                    impressions=e.impressions,
                    clicks=e.clicks,
                    conversions=e.conversions,
                    conversion_type=e.conversion_type,
                    attribution_window=e.attribution_window,
                    original_currency=e.original_currency,
                    reporting_currency=e.reporting_currency,
                    fx_rate=e.fx_rate,
                    fetched_at=e.fetched_at,
                    data_freshness_minutes=e.data_freshness_minutes,
                    trace_id=e.trace_id,
                )
            )
        return result

    async def save_proposal(self, proposal: ActionProposal) -> None:
        entity = ActionProposalEntity(
            action_id=proposal.action_id,
            fingerprint=proposal.fingerprint,
            client_slug=proposal.client_slug,
            platform=proposal.platform.value,
            action=proposal.action.value,
            resource_id=proposal.resource_id,
            resource_name=proposal.resource_name,
            old_value=str(proposal.old_value) if proposal.old_value is not None else None,
            new_value=str(proposal.new_value) if proposal.new_value is not None else None,
            currency=proposal.currency,
            reason=proposal.reason,
            confidence=proposal.confidence,
            risk=proposal.risk.value,
            state=proposal.state.value,
            proposed_at=proposal.proposed_at,
        )
        self.session.add(entity)
        await self.session.commit()

    async def record_execution(self, exec_rec: ExecutionRecord) -> None:
        entity = ExecutionRecordEntity(
            execution_id=exec_rec.execution_id,
            action_id=exec_rec.action_id,
            fingerprint=exec_rec.fingerprint,
            platform=exec_rec.platform.value,
            state=exec_rec.state.value,
            pre_state_value=str(exec_rec.pre_state_value) if exec_rec.pre_state_value is not None else None,
            post_state_value=str(exec_rec.post_state_value) if exec_rec.post_state_value is not None else None,
            executed_at=exec_rec.executed_at,
            error_message=exec_rec.error_message,
            rollback_supported=exec_rec.rollback_supported,
            rolled_back=exec_rec.rolled_back,
        )
        self.session.add(entity)
        await self.session.commit()
