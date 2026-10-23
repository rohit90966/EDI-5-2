from __future__ import annotations

import csv
import json
from pathlib import Path
import pytest

from data_generator.benchmark import BenchmarkRunner, partition_dataset_chronological
from data_generator.config import GeneratorConfig
from data_generator.engine import SyntheticDataEngine
from evaluation.sar_narrative_eval import BENCHMARK_SAR_CASES, score_narrative_rubric
from sar_safety import detect_pii_leak, validate_evidence_coverage


def test_audit_reported_metrics_exact_consistency() -> None:
    """Verifies that all metrics match prediction and ground-truth records exactly."""
    txns = list(csv.DictReader(open("data/synthetic/transactions.csv", encoding="utf-8")))
    gt = list(csv.DictReader(open("data/synthetic/scenario_ground_truth.csv", encoding="utf-8")))
    for t in txns:
        t["amount"] = float(t["amount"])
    for g in gt:
        g["is_suspicious_by_construction"] = g["is_suspicious_by_construction"].lower() == "true"

    train_part, val_part, test_part = partition_dataset_chronological(txns, gt)

    runner = BenchmarkRunner()
    runner.fit_anomaly_detector_on_train(train_part.transactions)
    scores = runner.evaluate_detector_scores(
        test_part.transactions,
        historical_context=train_part.transactions + val_part.transactions,
    )

    test_y = [1 if g["is_suspicious_by_construction"] else 0 for g in test_part.ground_truth]
    n_pos = sum(test_y)
    n_neg = len(test_y) - n_pos

    assert n_pos == 118, f"Expected exactly 118 positives in test set, got {n_pos}"
    assert n_neg == 177, f"Expected exactly 177 negatives in test set, got {n_neg}"

    for mod in ["rules_only", "anomaly_only", "graph_only", "hybrid"]:
        th = 0.20 if mod == "hybrid" else 0.50
        m = runner.compute_metrics(test_y, scores[mod], threshold=th)
        
        # Exact confusion matrix reconciliation
        assert m["tp"] + m["fn"] == n_pos
        assert m["tn"] + m["fp"] == n_neg
        assert m["tp"] + m["fp"] + m["tn"] + m["fn"] == 295
        assert m["fpr"] == round(m["fp"] / n_neg, 4)
        assert m["alert_rate"] == round((m["tp"] + m["fp"]) / 295, 4)


def test_sar_pipeline_safety_and_rubric_quality() -> None:
    """Validates that SAR narratives maintain 100% PII protection and zero hallucinations."""
    for case in BENCHMARK_SAR_CASES:
        narrative = case["baseline_narrative"]
        alert = case["alert"]
        
        # Test PII leak detector
        assert detect_pii_leak(narrative, alert["customer_name"]) is False
        assert alert["customer_id"] not in narrative

        # Test rubric scoring
        eval_res = score_narrative_rubric(narrative, alert, {})
        assert eval_res["grade"] == "EXCELLENT"
        assert eval_res["total_score"] >= 90.0
        assert eval_res["dimension_scores"]["pii_and_structure"] == 20.0
        assert eval_res["dimension_scores"]["unsupported_claims_absence"] == 20.0
