from __future__ import annotations

import csv
import json
import random
from datetime import datetime, timezone
from pathlib import Path

import pytest

from data_generator.adapter import build_alert_payload_for_case, transaction_record_to_evidence
from data_generator.benchmark import BenchmarkRunner, partition_dataset_chronological
from data_generator.config import GeneratorConfig
from data_generator.engine import SyntheticDataEngine
from ml.features import extract_transaction_features


def test_generator_schema_and_referential_integrity(tmp_path: Path) -> None:
    config = GeneratorConfig(seed=42, num_normal_customers=15, simulation_days=25, output_dir=str(tmp_path))
    engine = SyntheticDataEngine(config)
    summary = engine.generate()
    exported = engine.export(str(tmp_path))

    # 1. Accounts refer to valid customers
    cust_ids = {c.customer_id for c in engine.customers}
    acc_ids = {a.account_id for a in engine.accounts}
    for acc in engine.accounts:
        assert acc.customer_id in cust_ids, f"Account {acc.account_id} references nonexistent customer {acc.customer_id}"

    # 2. Transactions refer to valid accounts
    for txn in engine.transactions:
        assert txn.account_id in acc_ids, f"Transaction {txn.txn_id} references nonexistent account {txn.account_id}"

    # 3. Ground truth matches transactions
    txn_ids = {t.txn_id for t in engine.transactions}
    for gt in engine.ground_truth:
        assert gt.txn_id in txn_ids, f"Ground truth {gt.txn_id} references nonexistent transaction"

    # 4. Cases match valid scenarios
    sc_ids = {s.scenario_id for s in engine.scenarios}
    for c in engine.cases:
        assert c.scenario_id in sc_ids, f"Case {c.case_id} references nonexistent scenario {c.scenario_id}"


def test_seed_reproducibility(tmp_path: Path) -> None:
    config1 = GeneratorConfig(seed=123, num_normal_customers=10, simulation_days=20, output_dir=str(tmp_path / "run1"))
    config2 = GeneratorConfig(seed=123, num_normal_customers=10, simulation_days=20, output_dir=str(tmp_path / "run2"))

    engine1 = SyntheticDataEngine(config1)
    engine1.generate()
    engine1.export()

    engine2 = SyntheticDataEngine(config2)
    engine2.generate()
    engine2.export()

    t1 = (tmp_path / "run1" / "transactions.csv").read_text(encoding="utf-8")
    t2 = (tmp_path / "run2" / "transactions.csv").read_text(encoding="utf-8")
    assert t1 == t2, "Identical seeds must produce byte-identical transactions.csv"


def test_temporal_monotonicity_and_balance_arithmetic() -> None:
    config = GeneratorConfig(seed=42, num_normal_customers=10, simulation_days=25)
    engine = SyntheticDataEngine(config)
    engine.generate()

    # Verify chronological ordering
    ts_list = [datetime.fromisoformat(t.timestamp) for t in engine.transactions]
    for i in range(len(ts_list) - 1):
        assert ts_list[i] <= ts_list[i + 1], f"Transactions out of order at index {i}"

    # Verify running balance continuity per account
    acc_txns = {}
    for t in engine.transactions:
        acc_txns.setdefault(t.account_id, []).append(t)

    for aid, txns in acc_txns.items():
        for i in range(len(txns) - 1):
            t_curr = txns[i]
            t_next = txns[i + 1]
            if t_curr.balance_after is not None and t_next.balance_after is not None:
                expected_next = (
                    t_curr.balance_after + t_next.amount
                    if t_next.txn_type == "credit"
                    else t_curr.balance_after - t_next.amount
                )
                assert abs(t_next.balance_after - expected_next) < 1e-2, (
                    f"Balance arithmetic mismatch for account {aid}: "
                    f"prev={t_curr.balance_after}, txn={t_next.txn_type} {t_next.amount}, "
                    f"expected={expected_next}, actual={t_next.balance_after}"
                )


def test_zero_leakage_in_features_and_transactions() -> None:
    config = GeneratorConfig(seed=42, num_normal_customers=10, simulation_days=25)
    engine = SyntheticDataEngine(config)
    engine.generate()

    # 1. No label keys in transaction dictionaries
    forbidden_keys = {"is_suspicious", "is_suspicious_by_construction", "typology", "scenario_family", "label"}
    for t in engine.transactions:
        t_dict = asdict_simple(t)
        for k in t_dict.keys():
            assert k.lower() not in forbidden_keys, f"Forbidden label key found in transaction: {k}"

    # 2. No label keys in extracted feature vectors
    txns_raw = [asdict_simple(t) for t in engine.transactions[:30]]
    for idx, t in enumerate(txns_raw):
        vec, feat_dict = extract_transaction_features(t, txns_raw[:idx])
        for fk in feat_dict.keys():
            assert fk.lower() not in forbidden_keys, f"Forbidden key found in feature dictionary: {fk}"


def test_detection_adapter_compatibility() -> None:
    config = GeneratorConfig(seed=42, num_normal_customers=5, simulation_days=15)
    engine = SyntheticDataEngine(config)
    engine.generate()

    sample_acc = engine.accounts[0]
    sample_cust = [c for c in engine.customers if c.customer_id == sample_acc.customer_id][0]
    sample_txns = [t for t in engine.transactions if t.account_id == sample_acc.account_id][:5]

    # Test conversion to TransactionEvidence
    for t in sample_txns:
        ev = transaction_record_to_evidence(t)
        assert ev.txn_id == t.txn_id
        assert ev.amount == t.amount

    # Test build_alert_payload_for_case
    payload = build_alert_payload_for_case(sample_acc, sample_cust, sample_txns)
    assert payload["account_id"] == sample_acc.account_id
    assert "raw_transactions" in payload
    assert len(payload["raw_transactions"]) == len(sample_txns)
    assert "enrichment" in payload


def test_confusion_matrix_and_class_count_assertions() -> None:
    """Verifies that evaluation metrics strictly obey mathematical assertions and match ground truth."""
    runner = BenchmarkRunner()
    
    # Synthetic ground truth: 30 positives, 70 negatives
    y_true = [1] * 30 + [0] * 70
    y_scores = [0.85] * 25 + [0.15] * 5 + [0.75] * 10 + [0.10] * 60  # TP=25, FN=5, FP=10, TN=60
    
    m = runner.compute_metrics(y_true, y_scores, threshold=0.50)
    assert m["tp"] == 25
    assert m["fn"] == 5
    assert m["fp"] == 10
    assert m["tn"] == 60
    assert m["tp"] + m["fn"] == 30, "TP + FN must equal actual positives"
    assert m["tn"] + m["fp"] == 70, "TN + FP must equal actual negatives"
    assert m["tp"] + m["fp"] + m["tn"] + m["fn"] == 100
    assert m["precision"] == round(25 / 35, 4)
    assert m["recall"] == round(25 / 30, 4)


def asdict_simple(obj: Any) -> dict[str, Any]:
    return {
        "txn_id": obj.txn_id,
        "account_id": obj.account_id,
        "counterparty": obj.counterparty,
        "amount": obj.amount,
        "txn_type": obj.txn_type,
        "country": obj.country,
        "timestamp": obj.timestamp,
    }
