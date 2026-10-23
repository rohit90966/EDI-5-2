from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from data_generator.benchmark import BenchmarkRunner, partition_dataset_chronological
from data_generator.config import GeneratorConfig
from data_generator.engine import SyntheticDataEngine


def run_generation_and_benchmark(seed: int = 42, output_dir: str = "data/synthetic") -> None:
    print(f"=== 1. Generating Synthetic AML Dataset (seed={seed}) ===")
    config = GeneratorConfig(seed=seed, output_dir=output_dir)
    engine = SyntheticDataEngine(config)
    summary = engine.generate()
    print("Generation complete:")
    for k, v in summary.items():
        print(f"  {k}: {v}")

    exported = engine.export(output_dir)
    print("\nExported files:")
    for name, path in exported.items():
        print(f"  {name}: {path}")

    # Load back transactions and ground truth for benchmark
    print("\n=== 2. Partitioning Dataset Chronologically ===")
    with open(exported["transactions"], "r", encoding="utf-8") as f:
        txns = list(csv.DictReader(f))
    with open(exported["ground_truth"], "r", encoding="utf-8") as f:
        gt = list(csv.DictReader(f))

    # Convert amounts
    for t in txns:
        t["amount"] = float(t["amount"])
    for g in gt:
        g["is_suspicious_by_construction"] = g["is_suspicious_by_construction"].lower() == "true"

    train_part, val_part, test_part = partition_dataset_chronological(txns, gt)
    print(f"Train set: {len(train_part.transactions)} txns")
    print(f"Val set:   {len(val_part.transactions)} txns")
    print(f"Test set:  {len(test_part.transactions)} txns")

    runner = BenchmarkRunner()

    print("\n=== 3. Fitting Isolation Forest on Train Partition ===")
    runner.fit_anomaly_detector_on_train(train_part.transactions)

    print("\n=== 4. Validation Set Evaluation & Threshold Calibration ===")
    val_y_true = [1 if g["is_suspicious_by_construction"] else 0 for g in val_part.ground_truth]
    val_scores = runner.evaluate_detector_scores(val_part.transactions, historical_context=train_part.transactions)
    
    # Select best threshold for hybrid on validation set
    best_thresh = 0.50
    best_f1 = -1.0
    for cand_thresh in [0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60]:
        m = runner.compute_metrics(val_y_true, val_scores["hybrid"], threshold=cand_thresh)
        if m["f1"] > best_f1:
            best_f1 = m["f1"]
            best_thresh = cand_thresh
    print(f"Selected Validation Threshold for Hybrid: {best_thresh} (Val F1: {best_f1:.4f})")

    print("\n=== 5. Final Test Set Evaluation (Unseen Data) ===")
    test_y_true = [1 if g["is_suspicious_by_construction"] else 0 for g in test_part.ground_truth]
    test_scores = runner.evaluate_detector_scores(
        test_part.transactions,
        historical_context=train_part.transactions + val_part.transactions
    )

    models = ["rules_only", "anomaly_only", "graph_only", "hybrid"]
    results = {}
    for mod in models:
        th = best_thresh if mod == "hybrid" else 0.50
        res = runner.compute_metrics(test_y_true, test_scores[mod], threshold=th)
        results[mod] = res
        print(f"\n--- Model: {mod.upper()} (threshold={th}) ---")
        print(f"  Precision: {res['precision']:.4f} | Recall: {res['recall']:.4f} | F1: {res['f1']:.4f}")
        print(f"  ROC-AUC:   {res['roc_auc']:.4f}   | PR-AUC: {res['pr_auc']:.4f}")
        print(f"  Confusion Matrix: TP={res['tp']}, FP={res['fp']}, TN={res['tn']}, FN={res['fn']}")
        print(f"  FPR:       {res['fpr']:.4f}   | Alert Rate: {res['alert_rate']:.4f}")

    # Save benchmark report to reports/synthetic_dataset_report.json
    rep_dir = ROOT_DIR / "reports"
    rep_dir.mkdir(parents=True, exist_ok=True)
    report_data = {
        "dataset_summary": summary,
        "partitions": {
            "train_size": len(train_part.transactions),
            "val_size": len(val_part.transactions),
            "test_size": len(test_part.transactions),
        },
        "selected_validation_threshold": best_thresh,
        "test_results": results,
    }
    with open(rep_dir / "synthetic_dataset_report.json", "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)
    print(f"\nBenchmark report successfully saved to reports/synthetic_dataset_report.json")


if __name__ == "__main__":
    run_generation_and_benchmark()
