"""Strict Pydantic contracts for multi-agent interactions."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from agency_engine.domain.enums import QualityStatus, RiskLevel
from agency_engine.domain.models import ActionProposal, Evidence


class AnalystOutput(BaseModel):
    status: QualityStatus
    data_quality_score: float = Field(ge=0.0, le=1.0)
    anomalies_detected: list[str] = Field(default_factory=list)
    kpis_by_platform: dict[str, dict[str, Any]] = Field(default_factory=dict)
    evidence: list[Evidence] = Field(default_factory=list)
    notes: str = ""


class ComplianceOutput(BaseModel):
    status: QualityStatus
    policy_violations: list[str] = Field(default_factory=list)
    account_restrictions: list[str] = Field(default_factory=list)
    is_safe_to_proceed: bool
    evidence: list[Evidence] = Field(default_factory=list)
    notes: str = ""


class MediaBuyerOutput(BaseModel):
    proposals: list[ActionProposal] = Field(default_factory=list)
    summary: str = ""


class RiskOutput(BaseModel):
    level: RiskLevel
    confidence: float = Field(ge=0.0, le=1.0)
    blast_radius_score: float = Field(ge=0.0, le=1.0)  # 0 to 1
    passed: bool
    risk_factors: list[str] = Field(default_factory=list)


class VerifierOutput(BaseModel):
    status: QualityStatus
    arithmetic_valid: bool
    evidence_confirmed: bool
    upstream_state_matches: bool
    discrepancies: list[str] = Field(default_factory=list)
    notes: str = ""


class ConsensusDecision(BaseModel):
    action_id: str
    approved: bool
    execution_permitted: bool
    autonomy_mode: str
    reasons: list[str] = Field(default_factory=list)
    block_reasons: list[str] = Field(default_factory=list)
    proposal: ActionProposal
