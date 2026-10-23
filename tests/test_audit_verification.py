from __future__ import annotations

import copy
import threading
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

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
    CompositeScoreResult,
    DetectionFinding,
    DetectorExecutionResult,
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
from rag_pipeline.rule_engine import evaluate_rules, load_rule_config


# ═══════════════════════════════════════════════════════════════════════
# 1. RULE DETECTOR AUDIT: POSITIVE, NEGATIVE, BOUNDARY TESTS
# ═══════════════════════════════════════════════════════════════════════

def test_rule_aml001_structuring_boundary() -> None:
    config = load_rule_config()
    # Threshold is 20
    # Negative: count = 20 (not > 20)
    alert_neg = {
        "transactions": {"transaction_count": 20, "time_window_days": 3, "total_amount": 50000},
        "customer_profile": "Student",
    }
    blocks_neg = evaluate_rules(alert_neg, config)
    assert not any(b["rule_id"] == "AML-001" for b in blocks_neg)

    # Positive boundary: count = 21 (> 20)
    alert_pos = {
        "transactions": {"transaction_count": 21, "time_window_days": 3, "total_amount": 50000},
        "customer_profile": "Student",
    }
    blocks_pos = evaluate_rules(alert_pos, config)
    b001 = next(b for b in blocks_pos if b["rule_id"] == "AML-001")
    assert b001["rule_id"] == "AML-001"
    assert "FIU-IND" in b001["audit_reason"]["regulation"]


def test_rule_aml002_velocity_boundary() -> None:
    config = load_rule_config()
    # Threshold velocity is 5 txn/day
    # Boundary: 15 txns in 3 days = 5.0 txn/day (not > 5)
    alert_neg = {
        "transactions": {"transaction_count": 15, "time_window_days": 3, "total_amount": 50000},
        "customer_profile": "Student",
    }
    blocks_neg = evaluate_rules(alert_neg, config)
    assert not any(b["rule_id"] == "AML-002" for b in blocks_neg)

    # Positive: 16 txns in 3 days = 5.33 txn/day (> 5)
    alert_pos = {
        "transactions": {"transaction_count": 16, "time_window_days": 3, "total_amount": 50000},
        "customer_profile": "Student",
    }
    blocks_pos = evaluate_rules(alert_pos, config)
    assert any(b["rule_id"] == "AML-002" for b in blocks_pos)


def test_rule_aml004_large_value_boundary() -> None:
    config = load_rule_config()
    # Threshold is 1,000,000 INR
    # Negative: 1,000,000 exactly (gt is false)
    alert_neg = {
        "transactions": {"transaction_count": 1, "time_window_days": 1, "total_amount": 1000000},
        "customer_profile": "Salaried employee",
    }
    blocks_neg = evaluate_rules(alert_neg, config)
    assert not any(b["rule_id"] == "AML-004" for b in blocks_neg)

    # Positive: 1,000,001
    alert_pos = {
        "transactions": {"transaction_count": 1, "time_window_days": 1, "total_amount": 1000001},
        "customer_profile": "Salaried employee",
    }
    blocks_pos = evaluate_rules(alert_pos, config)
    assert any(b["rule_id"] == "AML-004" for b in blocks_pos)


def test_rule_aml005_profile_inconsistency() -> None:
    config = load_rule_config()
    # Student profile max is 100,000 INR
    alert_student_ok = {
        "transactions": {"transaction_count": 1, "time_window_days": 1, "total_amount": 100000},
        "customer_profile": "Student",
    }
    assert not any(b["rule_id"] == "AML-005" for b in evaluate_rules(alert_student_ok, config))

    alert_student_breach = {
        "transactions": {"transaction_count": 1, "time_window_days": 1, "total_amount": 100001},
        "customer_profile": "Student",
    }
    blocks = evaluate_rules(alert_student_breach, config)
    b005 = next(b for b in blocks if b["rule_id"] == "AML-005")
    assert "Student" in b005["observation"]
    assert "PMLA KYC" in b005["audit_reason"]["regulation"]


def test_rule_aml006_jurisdiction_matching() -> None:
    config = load_rule_config()
    # UAE is in high-risk list
    alert_uae = {
        "transactions": {"destination_country": "UAE", "transaction_count": 1, "time_window_days": 1},
        "customer_profile": "Student",
    }
    blocks = evaluate_rules(alert_uae, config)
    assert any(b["rule_id"] == "AML-006" for b in blocks)

    # US is not in high-risk list
    alert_us = {
        "transactions": {"destination_country": "US", "transaction_count": 1, "time_window_days": 1},
        "customer_profile": "Student",
    }
    blocks_us = evaluate_rules(alert_us, config)
    assert not any(b["rule_id"] == "AML-006" for b in blocks_us)


# ═══════════════════════════════════════════════════════════════════════
# 2. ISOLATION FOREST AUDIT: COLD START, MISSING, EXTREMES, LEAKAGE
# ═══════════════════════════════════════════════════════════════════════

def test_isolation_forest_empty_transactions() -> None:
    detector = IsolationForestDetector()
    res = detector.analyze_transactions([])
    assert res.status == DetectorStatus.INSUFFICIENT_DATA
    assert res.normalized_score == 0.0
    assert len(res.findings) == 0


def test_isolation_forest_extreme_outlier_handling() -> None:
    detector = IsolationForestDetector()
    # Reference training transactions: routine 500-1000 INR
    txns = [
        {"txn_id": f"T{i}", "amount": 800 + (i * 20), "timestamp": f"2026-01-0{i+1}T10:00:00Z"}
        for i in range(8)
    ]
    # Add an extreme outlier transaction: 50,000,000 INR
    txns.append({"txn_id": "T_MASSIVE", "amount": 50000000.0, "timestamp": "2026-01-09T10:00:00Z"})

    res = detector.analyze_transactions(txns)
    assert res.status == DetectorStatus.COMPLETE
    massive_findings = [f for f in res.findings if "T_MASSIVE" in f.evidence_txns]
    assert len(massive_findings) >= 1
    assert massive_findings[0].severity in (Severity.CRITICAL, Severity.HIGH)


def test_isolation_forest_duplicate_transactions() -> None:
    detector = IsolationForestDetector()
    # Duplicate transactions with identical timestamps and amounts
    txns = [
        {"txn_id": "T1", "amount": 5000, "timestamp": "2026-01-01T10:00:00Z"},
        {"txn_id": "T1", "amount": 5000, "timestamp": "2026-01-01T10:00:00Z"},
        {"txn_id": "T2", "amount": 5000, "timestamp": "2026-01-02T10:00:00Z"},
        {"txn_id": "T3", "amount": 5000, "timestamp": "2026-01-03T10:00:00Z"},
        {"txn_id": "T4", "amount": 5000, "timestamp": "2026-01-04T10:00:00Z"},
        {"txn_id": "T5", "amount": 5000, "timestamp": "2026-01-05T10:00:00Z"},
    ]
    # Must process without NaN or divide-by-zero crashes
    res = detector.analyze_transactions(txns)
    assert res.status == DetectorStatus.COMPLETE


# ═══════════════════════════════════════════════════════════════════════
# 3. GRAPH DETECTOR AUDIT: TIMESTAMPS, BOUNDS, SELF-LOOPS, BUDGETS
# ═══════════════════════════════════════════════════════════════════════

def test_graph_pass_through_timing_boundary() -> None:
    detector = GraphLaunderingDetector(pass_through_hours=72.0)

    # Inbound: Day 1 10:00
    # Outbound: 71 hours later (within 72h) -> POSITIVE
    txns_in_window = [
        {"txn_id": "T_IN", "account_id": "ACC_M", "counterparty": "CP_A", "amount": 1000000, "txn_type": "credit", "timestamp": "2026-01-01T10:00:00Z"},
        {"txn_id": "T_OUT", "account_id": "ACC_M", "counterparty": "CP_B", "amount": 950000, "txn_type": "debit", "timestamp": "2026-01-04T09:00:00Z"},
    ]
    res_pos = detector.analyze(txns_in_window)
    assert any(f.finding_code == "RAPID_PASS_THROUGH" for f in res_pos.findings)

    # Outbound: 75 hours later (exceeds 72h) -> NEGATIVE
    txns_out_window = [
        {"txn_id": "T_IN", "account_id": "ACC_M", "counterparty": "CP_A", "amount": 1000000, "txn_type": "credit", "timestamp": "2026-01-01T10:00:00Z"},
        {"txn_id": "T_OUT", "account_id": "ACC_M", "counterparty": "CP_B", "amount": 950000, "txn_type": "debit", "timestamp": "2026-01-04T13:00:00Z"},
    ]
    res_neg = detector.analyze(txns_out_window)
    assert not any(f.finding_code == "RAPID_PASS_THROUGH" for f in res_neg.findings)


def test_graph_cycle_length_bounds() -> None:
    detector = GraphLaunderingDetector(max_cycle_length=4)
    # Construct a cycle of length 5: A -> B -> C -> D -> E -> A
    txns_5_cycle = [
        {"txn_id": "T1", "account_id": "N_A", "counterparty": "N_B", "amount": 100000, "txn_type": "debit", "timestamp": "2026-01-01T10:00:00Z"},
        {"txn_id": "T2", "account_id": "N_B", "counterparty": "N_C", "amount": 100000, "txn_type": "debit", "timestamp": "2026-01-01T11:00:00Z"},
        {"txn_id": "T3", "account_id": "N_C", "counterparty": "N_D", "amount": 100000, "txn_type": "debit", "timestamp": "2026-01-01T12:00:00Z"},
        {"txn_id": "T4", "account_id": "N_D", "counterparty": "N_E", "amount": 100000, "txn_type": "debit", "timestamp": "2026-01-01T13:00:00Z"},
        {"txn_id": "T5", "account_id": "N_E", "counterparty": "N_A", "amount": 100000, "txn_type": "debit", "timestamp": "2026-01-01T14:00:00Z"},
    ]
    # Because max_cycle_length is 4, length 5 cycle must NOT be emitted as finding
    res = detector.analyze(txns_5_cycle)
    assert not any(f.finding_code == "CIRCULAR_FUNDS_FLOW" for f in res.findings)


def test_graph_self_loop_safety() -> None:
    detector = GraphLaunderingDetector()
    # Account transfers to itself
    txns = [
        {"txn_id": "T_SELF", "account_id": "ACC_X", "counterparty": "ACC_X", "amount": 50000, "txn_type": "debit", "timestamp": "2026-01-01T10:00:00Z"},
    ]
    res = detector.analyze(txns)
    # Must not crash or treat self-loop as circular money laundering loop
    assert not any(f.finding_code == "CIRCULAR_FUNDS_FLOW" for f in res.findings)


def test_graph_timeout_budget_exhaustion() -> None:
    # Set impossible budget: 0.000001 seconds
    detector = GraphLaunderingDetector(time_budget_sec=0.000001)
    txns = [
        {"txn_id": f"T{i}", "account_id": f"ACC_{i%10}", "counterparty": f"ACC_{(i+1)%10}", "amount": 1000, "txn_type": "debit", "timestamp": "2026-01-01T10:00:00Z"}
        for i in range(100)
    ]
    res = detector.analyze(txns)
    assert res.status == DetectorStatus.PARTIAL
    assert any("budget reached" in c.lower() for c in res.caveats)


# ═══════════════════════════════════════════════════════════════════════
# 4. RISK AGGREGATION & POLICY ENGINE AUDIT
# ═══════════════════════════════════════════════════════════════════════

def test_aggregator_all_combinations() -> None:
    agg = HybridRiskAggregator()

    # Case A: All COMPLETE
    res_a = agg.aggregate({
        "rules_engine": DetectorExecutionResult(detector_name="rules", detector_version="v1", status=DetectorStatus.COMPLETE, normalized_score=1.0),
        "isolation_forest": DetectorExecutionResult(detector_name="if", detector_version="v1", status=DetectorStatus.COMPLETE, normalized_score=1.0),
        "graph_detector": DetectorExecutionResult(detector_name="graph", detector_version="v1", status=DetectorStatus.COMPLETE, normalized_score=1.0),
    })
    assert res_a.overall_status == DetectorStatus.COMPLETE
    assert res_a.composite_score == 1.0

    # Case B: All FAILED -> overall FAILED
    res_b = agg.aggregate({
        "rules_engine": DetectorExecutionResult(detector_name="rules", detector_version="v1", status=DetectorStatus.FAILED),
        "isolation_forest": DetectorExecutionResult(detector_name="if", detector_version="v1", status=DetectorStatus.FAILED),
        "graph_detector": DetectorExecutionResult(detector_name="graph", detector_version="v1", status=DetectorStatus.FAILED),
    })
    assert res_b.overall_status == DetectorStatus.FAILED

    # Case C: All INSUFFICIENT_DATA -> overall INSUFFICIENT_DATA
    res_c = agg.aggregate({
        "rules_engine": DetectorExecutionResult(detector_name="rules", detector_version="v1", status=DetectorStatus.INSUFFICIENT_DATA),
        "isolation_forest": DetectorExecutionResult(detector_name="if", detector_version="v1", status=DetectorStatus.INSUFFICIENT_DATA),
        "graph_detector": DetectorExecutionResult(detector_name="graph", detector_version="v1", status=DetectorStatus.INSUFFICIENT_DATA),
    })
    assert res_c.overall_status == DetectorStatus.INSUFFICIENT_DATA


def test_policy_engine_multiple_rules_override() -> None:
    policy = AmlPolicyEngine()
    # Even if score is below 0.50 (e.g. 0.45), having 2 rules triggered makes case SAR draft eligible
    findings = [
        DetectionFinding(finding_id="F1", run_id="", detector_id="rules_engine", detector_version="v1", finding_code="AML-001", typology="Structuring", severity=Severity.MEDIUM, score=0.45, reason="Rule 1", reason_code="R1"),
        DetectionFinding(finding_id="F2", run_id="", detector_id="rules_engine", detector_version="v1", finding_code="AML-002", typology="Velocity", severity=Severity.MEDIUM, score=0.45, reason="Rule 2", reason_code="R2"),
    ]
    comp = CompositeScoreResult(
        composite_score=0.45,
        risk_tier="MEDIUM",
        detector_results={},
        overall_status=DetectorStatus.COMPLETE,
        data_quality_warnings=[],
        reason_codes=["R1", "R2"],
    )
    decision = policy.evaluate(comp, findings)
    assert decision.is_sar_draft_eligible is True
    assert decision.action == PolicyAction.SAR_DRAFT_ELIGIBLE


# ═══════════════════════════════════════════════════════════════════════
# 5. AUDIT LEDGER CONCURRENCY & TAMPER TESTS
# ═══════════════════════════════════════════════════════════════════════

def test_ledger_concurrent_thread_writes() -> None:
    reset_in_memory_ledger()
    num_threads = 10
    events_per_thread = 5

    def _worker(thread_id: int) -> None:
        for i in range(events_per_thread):
            append_ledger_block(
                f"CASE_{thread_id}",
                "THREAD_EVENT",
                {"thread_id": thread_id, "idx": i},
                actor_id=f"thread_{thread_id}",
            )

    threads = [threading.Thread(target=_worker, args=(t,)) for t in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Total events must equal num_threads * events_per_thread
    res = verify_ledger()
    assert res.is_valid is True
    assert res.verified_count == num_threads * events_per_thread


def test_ledger_payload_tampering_detected() -> None:
    reset_in_memory_ledger()
    append_ledger_block("C1", "EVENT_1", {"amount": 1000})
    append_ledger_block("C1", "EVENT_2", {"amount": 2000})
    append_ledger_block("C1", "EVENT_3", {"amount": 3000})

    from audit import ledger
    tampered = copy.deepcopy(ledger._in_memory_ledger)
    # Attacker alters transaction amount in payload
    tampered[1]["event_payload"]["amount"] = 999999999

    res = verify_ledger(tampered)
    assert res.is_valid is False
    assert res.first_failing_sequence == 2
    assert res.mismatch_category == "PAYLOAD_TAMPER"


def test_ledger_block_deletion_detected() -> None:
    reset_in_memory_ledger()
    append_ledger_block("C1", "EVENT_1", {"data": "step1"})
    append_ledger_block("C1", "EVENT_2", {"data": "step2"})
    append_ledger_block("C1", "EVENT_3", {"data": "step3"})

    from audit import ledger
    tampered = copy.deepcopy(ledger._in_memory_ledger)
    # Attacker deletes intermediate block 2
    del tampered[1]

    res = verify_ledger(tampered)
    assert res.is_valid is False
    assert res.mismatch_category == "SEQUENCE_GAP"


def test_ledger_block_reordering_detected() -> None:
    reset_in_memory_ledger()
    append_ledger_block("C1", "EVENT_1", {"data": "step1"})
    append_ledger_block("C1", "EVENT_2", {"data": "step2"})
    append_ledger_block("C1", "EVENT_3", {"data": "step3"})

    from audit import ledger
    tampered = copy.deepcopy(ledger._in_memory_ledger)
    # Attacker swaps sequence numbers between block 2 and 3
    tampered[1]["sequence_number"] = 3
    tampered[2]["sequence_number"] = 2

    res = verify_ledger(tampered)
    assert res.is_valid is False
    assert res.mismatch_category in ("LINK_TAMPER", "HASH_TAMPER", "SEQUENCE_GAP")


def test_ledger_full_chain_rewriting_threat_model() -> None:
    """
    Honest threat model verification:
    Demonstrates that an attacker who possesses write access to the database
    CAN recompute the entire hash chain from scratch if no external anchor exists.
    Internal verify_ledger() validates mathematical chain consistency, but cannot
    prevent total database rewriting without external PKI/blockchain anchoring.
    """
    reset_in_memory_ledger()
    append_ledger_block("C1", "EVENT_1", {"val": 10})
    append_ledger_block("C1", "EVENT_2", {"val": 20})
    append_ledger_block("C1", "EVENT_3", {"val": 30})

    from audit import ledger
    tampered = copy.deepcopy(ledger._in_memory_ledger)
    # Attacker modifies block 2 and maliciously recalculates all subsequent hashes
    tampered[1]["event_payload"]["val"] = 999
    tampered[1]["payload_hash"] = compute_payload_hash(tampered[1]["event_payload"])
    tampered[1]["block_hash"] = compute_block_hash(
        sequence_number=2,
        event_uuid=tampered[1]["event_uuid"],
        action_type=tampered[1]["action_type"],
        actor_id=tampered[1]["actor_id"],
        timestamp=tampered[1]["created_at"],
        aggregate_type=tampered[1]["aggregate_type"],
        aggregate_id=tampered[1]["aggregate_id"],
        payload_hash=tampered[1]["payload_hash"],
        prev_hash=tampered[0]["block_hash"],
    )

    tampered[2]["prev_hash"] = tampered[1]["block_hash"]
    tampered[2]["block_hash"] = compute_block_hash(
        sequence_number=3,
        event_uuid=tampered[2]["event_uuid"],
        action_type=tampered[2]["action_type"],
        actor_id=tampered[2]["actor_id"],
        timestamp=tampered[2]["created_at"],
        aggregate_type=tampered[2]["aggregate_type"],
        aggregate_id=tampered[2]["aggregate_id"],
        payload_hash=tampered[2]["payload_hash"],
        prev_hash=tampered[2]["prev_hash"],
    )

    # Mathematically, the rewritten chain is internally self-consistent:
    res = verify_ledger(tampered)
    assert res.is_valid is True
    # This proves why external anchoring (or external notary) is fundamentally required
    # to defend against database administrators rewriting the local database.


# ═══════════════════════════════════════════════════════════════════════
# 6. API AUTH GUARD TESTS FOR NEW ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════

def test_api_auth_guard_on_new_endpoints() -> None:
    from backend.app import app
    client = TestClient(app)

    # Missing auth header must return 401 Unauthorized
    r1 = client.get("/cases/some-case-id/analysis-runs")
    assert r1.status_code == 401

    r2 = client.get("/cases/some-case-id/analysis-runs/latest")
    assert r2.status_code == 401

    r3 = client.get("/analysis-runs/some-run-id")
    assert r3.status_code == 401

    r4 = client.get("/analysis-runs/some-run-id/findings")
    assert r4.status_code == 401

    r5 = client.get("/audit/ledger/verify")
    assert r5.status_code == 401
