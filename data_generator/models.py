from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class CustomerProfile:
    customer_id: str
    name: str
    occupation: str
    monthly_income: float
    risk_rating: str  # LOW, MEDIUM, HIGH


@dataclass
class AccountRecord:
    account_id: str
    customer_id: str
    account_type: str  # savings, current
    opened_date: str  # ISO 8601
    initial_balance: float = 10000.0
    current_balance: float = 10000.0


@dataclass
class TransactionRecord:
    txn_id: str
    account_id: str
    counterparty: str
    amount: float
    txn_type: str  # debit, credit
    country: str
    timestamp: str  # ISO 8601
    balance_after: float | None = None
    purpose_code: str = "TRANSFER"


@dataclass
class ScenarioRecord:
    scenario_id: str
    scenario_family: str  # e.g., STRUCTURING, PASS_THROUGH, CIRCULAR_FLOW, FAN_IN_FAN_OUT, BENIGN_CONTROL
    typology: str
    is_suspicious_by_construction: bool
    involved_accounts: list[str] = field(default_factory=list)
    involved_txns: list[str] = field(default_factory=list)
    start_time: str = ""
    end_time: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    notes: str = ""


@dataclass
class GroundTruthRecord:
    txn_id: str
    account_id: str
    scenario_id: str
    scenario_family: str
    typology: str
    is_suspicious_by_construction: bool
    is_contextual_only: bool  # True if benign transaction in an account that also has suspicious activity
    confidence: float = 1.0


@dataclass
class InvestigationCaseRecord:
    case_id: str
    scenario_id: str
    account_id: str
    alert_type: str
    alert_timestamp: str
    window_start: str
    window_end: str
    ground_truth_typology: str
    is_suspicious: bool
    transaction_ids: list[str] = field(default_factory=list)
