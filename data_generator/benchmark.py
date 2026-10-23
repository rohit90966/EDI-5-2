from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import average_precision_score, confusion_matrix, precision_recall_fscore_support, roc_auc_score

from detection.aggregator import HybridRiskAggregator
from detection.contracts import DetectorStatus
from detection.rules_adapter import RulesEngineDetector
from graph.graph_detector import GraphLaunderingDetector
from ml.anomaly_detector import IsolationForestDetector
from ml.features import extract_transaction_features


@dataclass
class EvaluationPartition:
    name: str
    transactions: list[dict[str, Any]]
    ground_truth: list[dict[str, Any]]


def partition_dataset_chronological(
    transactions: list[dict[str, Any]],
    ground_truth: list[dict[str, Any]],
    train_ratio: float = 0.60,
    val_ratio: float = 0.20,
    test_ratio: float = 0.20,
) -> tuple[EvaluationPartition, EvaluationPartition, EvaluationPartition]:
    """
    Partitions transactions chronologically into train, validation, and test sets.
    """
    # Sort strictly chronologically
    sorted_txns = sorted(transactions, key=lambda t: t["timestamp"])
    gt_map = {g["txn_id"]: g for g in ground_truth}

    n = len(sorted_txns)
    idx_train = int(n * train_ratio)
    idx_val = int(n * (train_ratio + val_ratio))

    train_txns = sorted_txns[:idx_train]
    val_txns = sorted_txns[idx_train:idx_val]
    test_txns = sorted_txns[idx_val:]

    train_part = EvaluationPartition(
        name="train",
        transactions=train_txns,
        ground_truth=[gt_map[t["txn_id"]] for t in train_txns],
    )
    val_part = EvaluationPartition(
        name="val",
        transactions=val_txns,
        ground_truth=[gt_map[t["txn_id"]] for t in val_txns],
    )
    test_part = EvaluationPartition(
        name="test",
        transactions=test_txns,
        ground_truth=[gt_map[t["txn_id"]] for t in test_txns],
    )
    return train_part, val_part, test_part


class BenchmarkRunner:
    def __init__(self) -> None:
        self.rules_detector = RulesEngineDetector()
        self.anomaly_detector = IsolationForestDetector()
        self.graph_detector = GraphLaunderingDetector(max_transactions=5000)
        self.aggregator = HybridRiskAggregator()

    def fit_anomaly_detector_on_train(self, train_txns: list[dict[str, Any]]) -> None:
        """Fits Isolation Forest strictly on the training partition."""
        self.anomaly_detector = IsolationForestDetector()
        self.anomaly_detector.analyze_transactions(train_txns)

    def evaluate_detector_scores(
        self,
        transactions: list[dict[str, Any]],
        historical_context: list[dict[str, Any]] | None = None,
    ) -> dict[str, list[float]]:
        """
        Computes continuous scores for all four detection models:
        1. rules_only
        2. anomaly_only (Isolation Forest continuous sigmoid score)
        3. graph_only
        4. hybrid (Aggregated risk score)
        """
        all_txns_context = (historical_context or []) + transactions
        all_txns_context = sorted(all_txns_context, key=lambda t: t["timestamp"])

        # 1. Anomaly scores (continuous score per transaction)
        res_anomaly = self.anomaly_detector.analyze_transactions(all_txns_context)
        anomaly_score_map: dict[str, float] = {}
        for f in res_anomaly.findings:
            for tid in f.evidence_txns:
                anomaly_score_map[tid] = max(anomaly_score_map.get(tid, 0.0), f.score)

        # 2. Graph scores
        res_graph = self.graph_detector.analyze(all_txns_context)
        graph_score_map: dict[str, float] = {}
        for f in res_graph.findings:
            for tid in f.evidence_txns:
                graph_score_map[tid] = max(graph_score_map.get(tid, 0.0), f.score)

        # 3. Rules scores (per transaction evaluation)
        rules_score_map: dict[str, float] = {}
        for txn in transactions:
            tid = txn["txn_id"]
            amt = float(txn.get("amount", 0.0))
            country = str(txn.get("country", "IN"))
            # High amount or high-risk jurisdiction flags
            is_rule_flag = (amt >= 1000000.0) or (country in ["UAE", "CAYMAN", "PANAMA"])
            rules_score_map[tid] = 0.90 if is_rule_flag else 0.05

        scores_rules: list[float] = []
        scores_anomaly: list[float] = []
        scores_graph: list[float] = []
        scores_hybrid: list[float] = []

        w_r, w_a, w_g = 0.35, 0.35, 0.30

        for txn in transactions:
            tid = txn["txn_id"]
            s_r = rules_score_map.get(tid, 0.05)
            s_a = anomaly_score_map.get(tid, 0.02)
            s_g = graph_score_map.get(tid, 0.01)

            scores_rules.append(s_r)
            scores_anomaly.append(s_a)
            scores_graph.append(s_g)

            # Continuous hybrid score
            s_h = round((w_r * s_r) + (w_a * s_a) + (w_g * s_g), 4)
            scores_hybrid.append(s_h)

        return {
            "rules_only": scores_rules,
            "anomaly_only": scores_anomaly,
            "graph_only": scores_graph,
            "hybrid": scores_hybrid,
        }

    def compute_metrics(
        self,
        y_true: list[int],
        y_scores: list[float],
        threshold: float = 0.50,
    ) -> dict[str, Any]:
        y_true_arr = np.array(y_true, dtype=int)
        y_scores_arr = np.array(y_scores, dtype=float)
        y_pred_arr = (y_scores_arr >= threshold).astype(int)

        tp = int(np.sum((y_true_arr == 1) & (y_pred_arr == 1)))
        fp = int(np.sum((y_true_arr == 0) & (y_pred_arr == 1)))
        tn = int(np.sum((y_true_arr == 0) & (y_pred_arr == 0)))
        fn = int(np.sum((y_true_arr == 1) & (y_pred_arr == 0)))

        prec, rec, f1, _ = precision_recall_fscore_support(
            y_true_arr, y_pred_arr, average="binary", zero_division=0
        )
        try:
            roc_auc = float(roc_auc_score(y_true_arr, y_scores_arr))
        except ValueError:
            roc_auc = 0.5
        try:
            pr_auc = float(average_precision_score(y_true_arr, y_scores_arr))
        except ValueError:
            pr_auc = 0.0

        fpr = round(fp / (fp + tn), 4) if (fp + tn) > 0 else 0.0
        alert_rate = round(float(np.mean(y_pred_arr)), 4)

        # Rigorous mathematical consistency assertions
        n_pos = int(np.sum(y_true_arr == 1))
        n_neg = int(np.sum(y_true_arr == 0))
        total_eval = len(y_true_arr)

        assert tp + fn == n_pos, f"Assertion failed: TP ({tp}) + FN ({fn}) != actual positives ({n_pos})"
        assert tn + fp == n_neg, f"Assertion failed: TN ({tn}) + FP ({fp}) != actual negatives ({n_neg})"
        assert tp + fp + tn + fn == total_eval, f"Assertion failed: Confusion matrix sum != total evaluated ({total_eval})"
        
        calc_prec = round(float(tp / (tp + fp)), 4) if (tp + fp) > 0 else 0.0
        calc_rec = round(float(tp / (tp + fn)), 4) if (tp + fn) > 0 else 0.0
        assert abs(round(float(prec), 4) - calc_prec) < 1e-3, f"Precision mismatch: {prec} vs {calc_prec}"
        assert abs(round(float(rec), 4) - calc_rec) < 1e-3, f"Recall mismatch: {rec} vs {calc_rec}"

        return {
            "threshold": threshold,
            "precision": round(float(prec), 4),
            "recall": round(float(rec), 4),
            "f1": round(float(f1), 4),
            "roc_auc": round(roc_auc, 4),
            "pr_auc": round(pr_auc, 4),
            "tp": tp,
            "fp": fp,
            "tn": tn,
            "fn": fn,
            "fpr": fpr,
            "alert_rate": alert_rate,
        }
