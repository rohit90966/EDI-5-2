from __future__ import annotations

import copy
from datetime import datetime, timezone
import pytest

from audit.ledger import (
    GENESIS_PREV_HASH,
    append_ledger_block,
    canonical_serialize,
    compute_block_hash,
    compute_payload_hash,
    reset_in_memory_ledger,
    verify_ledger,
)
from detection.aggregator import HybridRiskAggregator
from detection.contracts import (
    DetectorStatus,
    PolicyAction,
    Severity,
)
from detection.policy import AmlPolicyEngine
from detection.rules_adapter import RulesEngineDetector
from detection.service import MultiDetectorService
from detection.snapshot import create_analysis_snapshot
from graph.graph_detector import GraphLaunderingDetector
from ml.anomaly_detector import IsolationForestDetector, sigmoid_normalize
from ml.features import extract_transaction_features


# ── 1. SNAPSHOT & FEATURE TESTS ────────────────────────────────────────

def test_canonical_snapshot_is_deterministic() -> None:
    alert = {
        "alert_id": "ALT_99",
        "customer_id": "CUST_99",
        "customer_name": "Test User",
        "transactions": {"time_window_days": 3},
        "raw_transactions": [
            {"txn_id": "T2", "amount": 200, "timestamp": "2026-03-02T10:00:00Z"},
            {"txn_id": "T1", "amount": 100, "timestamp": "2026-03-01T10:00:00Z"},
        ],
    }
    s1 = create_analysis_snapshot(alert, as_of_time="2026-03-03T12:00:00Z")
    s2 = create_analysis_snapshot(alert, as_of_time="2026-03-03T12:00:00Z")

    assert s1.snapshot_hash == s2.snapshot_hash
    assert len(s1.snapshot_hash) == 64
    # Ensure transactions are sorted deterministically
    assert s1.transactions[0]["txn_id"] == "T1"
    assert s1.transactions[1]["txn_id"] == "T2"


def test_feature_extraction_prevents_future_leakage() -> None:
    historical = [
        {"txn_id": "T1", "amount": 1000, "timestamp": "2026-01-01T10:00:00Z"},
        {"txn_id": "T2", "amount": 2000, "timestamp": "2026-01-02T10:00:00Z"},
        # Future transaction that should NOT influence T2 feature calculation
        {"txn_id": "T3_FUTURE", "amount": 5000000, "timestamp": "2026-01-10T10:00:00Z"},
    ]
    target_txn = historical[1]  # T2
    vec, feat_dict = extract_transaction_features(target_txn, historical, as_of_time="2026-01-02T12:00:00Z")

    # The 5,000,000 future transaction must not contaminate the rolling 24h/7d amounts
    assert feat_dict["rolling_amount_24h"] <= 3000.0
    assert feat_dict["rolling_amount_7d"] <= 3000.0


# ── 2. ISOLATION FOREST DETECTOR TESTS ─────────────────────────────────

def test_isolation_forest_handles_sparse_history_safely() -> None:
    detector = IsolationForestDetector()
    sparse_txns = [
        {"txn_id": "T1", "amount": 100, "timestamp": "2026-01-01T10:00:00Z"},
        {"txn_id": "T2", "amount": 200, "timestamp": "2026-01-02T10:00:00Z"},
    ]
    res = detector.analyze_transactions(sparse_txns)
    assert res.status == DetectorStatus.PARTIAL
    assert "fewer than 5" in res.caveats[0].lower()


def test_isolation_forest_score_normalization() -> None:
    # Highly negative decision_function (outlier) -> normalized score close to 1.0
    outlier_norm = sigmoid_normalize(-0.4)
    # Positive decision_function (inlier) -> normalized score close to 0.0
    inlier_norm = sigmoid_normalize(0.4)

    assert outlier_norm > 0.85
    assert inlier_norm < 0.15
    assert 0.0 <= outlier_norm <= 1.0


# ── 3. GRAPH DETECTOR TESTS ────────────────────────────────────────────

def test_graph_detects_rapid_pass_through() -> None:
    txns = [
        {"txn_id": "T_IN", "account_id": "ACC_MULE", "counterparty": "SOURCE_A", "amount": 1000000.0, "txn_type": "credit", "timestamp": "2026-02-01T10:00:00Z"},
        {"txn_id": "T_OUT", "account_id": "ACC_MULE", "counterparty": "DEST_B", "amount": 980000.0, "txn_type": "debit", "timestamp": "2026-02-01T14:00:00Z"},
    ]
    detector = GraphLaunderingDetector()
    res = detector.analyze(txns)

    assert res.status == DetectorStatus.COMPLETE
    assert len(res.findings) >= 1
    pt_findings = [f for f in res.findings if f.finding_code == "RAPID_PASS_THROUGH"]
    assert len(pt_findings) == 1
    assert "T_IN" in pt_findings[0].evidence_txns
    assert "T_OUT" in pt_findings[0].evidence_txns


def test_graph_detects_circular_flow() -> None:
    txns = [
        {"txn_id": "T1", "account_id": "NODE_A", "counterparty": "NODE_B", "amount": 500000, "txn_type": "debit", "timestamp": "2026-02-01T10:00:00Z"},
        {"txn_id": "T2", "account_id": "NODE_B", "counterparty": "NODE_C", "amount": 490000, "txn_type": "debit", "timestamp": "2026-02-01T12:00:00Z"},
        {"txn_id": "T3", "account_id": "NODE_C", "counterparty": "NODE_A", "amount": 485000, "txn_type": "debit", "timestamp": "2026-02-01T14:00:00Z"},
    ]
    detector = GraphLaunderingDetector()
    res = detector.analyze(txns)

    circ_findings = [f for f in res.findings if f.finding_code == "CIRCULAR_FUNDS_FLOW"]
    assert len(circ_findings) >= 1
    assert circ_findings[0].severity == Severity.CRITICAL


# ── 4. AGGREGATOR & POLICY TESTS ───────────────────────────────────────

def test_aggregator_rejects_invalid_weights() -> None:
    with pytest.raises(ValueError, match="Detector weights must sum to 1.0"):
        HybridRiskAggregator(weights={"rules": 0.5, "anomaly": 0.2})


def test_aggregator_does_not_convert_failure_to_zero() -> None:
    from detection.contracts import DetectorExecutionResult
    detector_results = {
        "rules_engine": DetectorExecutionResult(
            detector_name="rules_engine",
            detector_version="v1",
            status=DetectorStatus.FAILED,
            error_message="Configuration missing",
        ),
        "isolation_forest": DetectorExecutionResult(
            detector_name="isolation_forest",
            detector_version="v1",
            status=DetectorStatus.COMPLETE,
            normalized_score=0.8,
            weight=0.25,
            score_contribution=0.2,
        ),
        "graph_detector": DetectorExecutionResult(
            detector_name="graph_detector",
            detector_version="v1",
            status=DetectorStatus.COMPLETE,
            normalized_score=0.8,
            weight=0.40,
            score_contribution=0.32,
        ),
    }
    agg = HybridRiskAggregator()
    res = agg.aggregate(detector_results)

    # Status must be PARTIAL because one detector failed
    assert res.overall_status == DetectorStatus.PARTIAL
    assert any("failed during analysis" in w for w in res.data_quality_warnings)
    # Score should re-normalize over available active weights, NOT drop to 0
    assert res.composite_score >= 0.70


def test_policy_engine_escalation() -> None:
    policy = AmlPolicyEngine()
    agg = HybridRiskAggregator()
    
    # 1. High risk -> SAR draft eligible
    from detection.contracts import DetectionFinding
    crit_finding = DetectionFinding(
        finding_id="F1",
        run_id="R1",
        detector_id="graph",
        detector_version="v1",
        finding_code="CIRCULAR_FUNDS_FLOW",
        typology="Circular Flow",
        severity=Severity.CRITICAL,
        score=0.95,
        reason="Circular loop",
        reason_code="CIRC_FLOW",
    )
    from detection.contracts import CompositeScoreResult
    comp_result = CompositeScoreResult(
        composite_score=0.82,
        risk_tier="CRITICAL",
        detector_results={},
        overall_status=DetectorStatus.COMPLETE,
        data_quality_warnings=[],
        reason_codes=["CIRC_FLOW"],
    )
    decision = policy.evaluate(comp_result, [crit_finding])
    assert decision.action == PolicyAction.SAR_DRAFT_ELIGIBLE
    assert decision.is_sar_draft_eligible is True
    assert decision.requires_analyst_review is True


# ── 5. AUDIT LEDGER HASH CHAIN TESTS ───────────────────────────────────

def test_audit_ledger_verification_and_tamper_detection() -> None:
    reset_in_memory_ledger()

    # Append 3 events
    e1 = append_ledger_block("CASE_A", "CASE_CREATED", {"info": "init"})
    e2 = append_ledger_block("CASE_A", "RULES_EVALUATED", {"score": 0.5})
    e3 = append_ledger_block("CASE_A", "CASE_REVIEWED", {"decision": "APPROVE"})

    # Clean ledger must verify
    res_clean = verify_ledger()
    assert res_clean.is_valid is True
    assert res_clean.verified_count == 3

    # Tamper with block 2 payload
    from audit import ledger
    tampered = copy.deepcopy(ledger._in_memory_ledger)
    tampered[1]["event_payload"]["score"] = 0.05

    res_tampered = verify_ledger(tampered)
    assert res_tampered.is_valid is False
    assert res_tampered.first_failing_sequence == 2
    assert res_tampered.mismatch_category == "PAYLOAD_TAMPER"


# ── 6. MULTI-DETECTOR INTEGRATION TEST ─────────────────────────────────

def test_multi_detector_service_end_to_end() -> None:
    reset_in_memory_ledger()
    service = MultiDetectorService()

    alert = {
        "alert_id": "ALERT_TEST_01",
        "customer_id": "CUST_TEST",
        "customer_name": "Vikram Singh",
        "customer_profile": "Student",
        "alert_type": "Layering",
        "transactions": {
            "transaction_count": 25,
            "total_amount": 1200000,
            "time_window_days": 2,
            "destination_country": "UAE",
        },
        "raw_transactions": [
            {"txn_id": "TXN_01", "account_id": "ACC_V", "counterparty": "CP_1", "amount": 600000, "txn_type": "credit", "timestamp": "2026-03-01T10:00:00Z"},
            {"txn_id": "TXN_02", "account_id": "ACC_V", "counterparty": "CP_2", "amount": 590000, "txn_type": "debit", "timestamp": "2026-03-01T14:00:00Z", "country": "UAE"},
        ],
    }

    run_record = service.run_analysis(alert)

    assert run_record.run_id.startswith("RUN_")
    assert run_record.composite_score > 0.0
    assert len(run_record.snapshot_hash) == 64
    assert len(run_record.findings) >= 1
    assert "rules_engine" in run_record.detector_results
    assert "isolation_forest" in run_record.detector_results
    assert "graph_detector" in run_record.detector_results

    # Verify audit ledger recorded the run
    ledger_res = verify_ledger()
    assert ledger_res.is_valid is True
    assert ledger_res.verified_count >= 1
