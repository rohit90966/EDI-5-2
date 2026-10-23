from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class DetectorStatus(str, Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    SKIPPED = "SKIPPED"


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class PolicyAction(str, Enum):
    NO_ADDITIONAL_REVIEW_TRIGGERED = "NO_ADDITIONAL_REVIEW_TRIGGERED"
    ANALYST_REVIEW_REQUIRED = "ANALYST_REVIEW_REQUIRED"
    ENHANCED_REVIEW_REQUIRED = "ENHANCED_REVIEW_REQUIRED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    ANALYSIS_INCOMPLETE = "ANALYSIS_INCOMPLETE"
    SAR_DRAFT_ELIGIBLE = "SAR_DRAFT_ELIGIBLE"


class TransactionEvidence(BaseModel):
    model_config = ConfigDict(extra="ignore")

    txn_id: str
    amount: float
    timestamp: str
    txn_type: str = "debit"
    source_account: str | None = None
    destination_account: str | None = None
    country: str | None = None
    counterparty: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DetectionFinding(BaseModel):
    model_config = ConfigDict(extra="ignore")

    finding_id: str
    run_id: str
    detector_id: str
    detector_version: str
    finding_code: str
    typology: str
    severity: Severity
    score: float = Field(ge=0.0, le=1.0, description="Normalized score between 0.0 and 1.0")
    raw_score: float | None = None
    confidence_or_quality: float = Field(default=1.0, ge=0.0, le=1.0)
    reason: str
    reason_code: str
    evidence_txns: list[str] = Field(default_factory=list)
    evidence_entities: list[str] = Field(default_factory=list)
    computed_features: dict[str, Any] = Field(default_factory=dict)
    graph_path: list[str] | None = None
    data_quality_caveats: list[str] = Field(default_factory=list)
    safe_evidence_summary: str = ""


class DetectorExecutionResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    detector_name: str
    detector_version: str
    status: DetectorStatus
    raw_score: float | None = None
    normalized_score: float = 0.0
    weight: float = 0.0
    score_contribution: float = 0.0
    findings: list[DetectionFinding] = Field(default_factory=list)
    execution_time_ms: float = 0.0
    error_message: str | None = None
    caveats: list[str] = Field(default_factory=list)


class AnalysisSnapshot(BaseModel):
    model_config = ConfigDict(extra="ignore")

    snapshot_id: str
    as_of_time: str
    customer_id: str
    time_window_days: int
    start_time: str | None = None
    end_time: str | None = None
    transaction_count: int = 0
    transactions: list[dict[str, Any]] = Field(default_factory=list)
    customer_profile: dict[str, Any] = Field(default_factory=dict)
    snapshot_hash: str = ""


class CompositeScoreResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    composite_score: float = Field(ge=0.0, le=1.0)
    risk_tier: str
    detector_results: dict[str, DetectorExecutionResult] = Field(default_factory=dict)
    overall_status: DetectorStatus
    data_quality_warnings: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)
    config_version: str = "1.0.0"
    config_hash: str = ""


class PolicyDecision(BaseModel):
    model_config = ConfigDict(extra="ignore")

    action: PolicyAction
    is_sar_draft_eligible: bool
    requires_analyst_review: bool
    escalation_level: str
    policy_version: str = "1.0.0"
    rationale: list[str] = Field(default_factory=list)


class AnalysisRunRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")

    run_id: str
    case_id: str
    alert_id: str
    idempotency_key: str | None = None
    status: DetectorStatus
    created_at: str
    completed_at: str | None = None
    as_of_time: str
    snapshot_hash: str
    rules_version: str
    rules_hash: str
    composite_score: float
    risk_tier: str
    policy_action: PolicyAction
    policy_decision: PolicyDecision
    detector_results: dict[str, Any]
    findings: list[DetectionFinding]
    warnings: list[str] = Field(default_factory=list)
