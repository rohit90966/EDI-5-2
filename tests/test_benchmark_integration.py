from __future__ import annotations

import csv
import json
from pathlib import Path
import pytest

from data_generator.adapter import build_alert_payload_for_case
from data_generator.config import GeneratorConfig
from data_generator.engine import SyntheticDataEngine
from detection.contracts import PolicyAction
from detection.service import MultiDetectorService
from audit.ledger import verify_ledger, reset_in_memory_ledger


def test_integration_and_audit_ledger_verification() -> None:
    reset_in_memory_ledger()
    config = GeneratorConfig(seed=42, num_normal_customers=10, simulation_days=20)
    engine = SyntheticDataEngine(config)
    engine.generate()

    svc = MultiDetectorService()
    assert len(engine.cases) > 0

    # Process first 3 cases
    for c in engine.cases[:3]:
        acc = next(a for a in engine.accounts if a.account_id == c.account_id)
        cust = next(cu for cu in engine.customers if cu.customer_id == acc.customer_id)
        c_txns = [t for t in engine.transactions if t.txn_id in c.transaction_ids]
        h_txns = [t for t in engine.transactions if t.account_id == c.account_id and t.txn_id not in c.transaction_ids]
        
        payload = build_alert_payload_for_case(acc, cust, c_txns, h_txns)
        rec = svc.run_analysis(payload, case_id=c.case_id)

        assert rec.case_id == c.case_id
        assert rec.status.value in ["COMPLETE", "PARTIAL"]
        assert 0.0 <= rec.composite_score <= 1.0
        assert rec.rules_hash != ""
        assert rec.snapshot_hash != ""

    # Verify audit ledger integrity
    v_res = verify_ledger()
    assert v_res.is_valid is True
    assert v_res.verified_count >= 3


def test_evidence_to_transaction_traceability() -> None:
    config = GeneratorConfig(seed=42, num_normal_customers=5, simulation_days=15)
    engine = SyntheticDataEngine(config)
    engine.generate()

    all_tids = {t.txn_id for t in engine.transactions}
    svc = MultiDetectorService()

    # Find a structuring case
    struct_case = next((c for c in engine.cases if "STRUCTURING" in c.alert_type), engine.cases[0])
    acc = next(a for a in engine.accounts if a.account_id == struct_case.account_id)
    cust = next(cu for cu in engine.customers if cu.customer_id == acc.customer_id)
    c_txns = [t for t in engine.transactions if t.txn_id in struct_case.transaction_ids]

    payload = build_alert_payload_for_case(acc, cust, c_txns)
    rec = svc.run_analysis(payload, case_id=struct_case.case_id)

    # Assert all evidence transactions in findings trace back to actual input transactions
    for f in rec.findings:
        for ev_tid in f.evidence_txns:
            assert ev_tid in all_tids, f"Evidence transaction {ev_tid} is not in transaction dataset"
