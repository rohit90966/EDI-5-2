from __future__ import annotations

import json
import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from typing import Any
import numpy as np
from scipy import stats

from evaluation.evaluator import BenchmarkHarness
from evaluation.synthetic_generator import generate_benchmark_dataset

def run_multi_seed(seeds: list[int] = [42, 101, 202, 303, 404, 505, 606, 707, 808, 909]) -> dict[str, Any]:
    harness = BenchmarkHarness()
    models = ["rules_only", "anomaly_only", "graph_only", "hybrid_full"]
    metrics_keys = ["precision", "recall", "f1_score", "pr_auc", "roc_auc", "alert_rate"]

    collected: dict[str, dict[str, list[float]]] = {
        m: {k: [] for k in metrics_keys} for m in models
    }
    confusion_matrices: dict[str, list[dict[str, int]]] = {m: [] for m in models}
    typology_recalls: dict[str, dict[str, list[float]]] = {}

    for seed in seeds:
        txns, truth = generate_benchmark_dataset(seed=seed, normal_accounts_count=20)
        res = harness.run_benchmark(txns, truth)

        for m in ["rules_only", "anomaly_only", "graph_only"]:
            m_res = res["individual_detectors"][m]
            confusion_matrices[m].append(m_res["confusion_matrix"])
            for k in metrics_keys:
                collected[m][k].append(m_res[k])

        h_res = res["ablations"]["hybrid_full"]
        confusion_matrices["hybrid_full"].append(h_res["confusion_matrix"])
        for k in metrics_keys:
            collected["hybrid_full"][k].append(h_res[k])

        # Typology recalls
        for typ, data in res["typology_breakdown"].items():
            if typ not in typology_recalls:
                typology_recalls[typ] = {"rules": [], "anomaly": [], "graph": [], "hybrid": []}
            typology_recalls[typ]["rules"].append(data["recall_rules"])
            typology_recalls[typ]["anomaly"].append(data["recall_anomaly"])
            typology_recalls[typ]["graph"].append(data["recall_graph"])
            typology_recalls[typ]["hybrid"].append(data["recall_hybrid"])

    # Aggregate statistics
    summary: dict[str, Any] = {}
    for m in models:
        summary[m] = {}
        for k in metrics_keys:
            vals = np.array(collected[m][k])
            mean_val = float(np.mean(vals))
            std_val = float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0
            sem_val = float(stats.sem(vals)) if len(vals) > 1 else 0.0
            ci95 = float(sem_val * stats.t.ppf((1 + 0.95) / 2.0, len(vals) - 1)) if len(vals) > 1 else 0.0
            summary[m][k] = {
                "mean": round(mean_val, 4),
                "std": round(std_val, 4),
                "ci95_low": round(mean_val - ci95, 4),
                "ci95_high": round(mean_val + ci95, 4),
            }

    # Average confusion matrices
    avg_cms: dict[str, dict[str, float]] = {}
    for m in models:
        cms = confusion_matrices[m]
        avg_cms[m] = {
            "TP": round(float(np.mean([c["TP"] for c in cms])), 1),
            "FP": round(float(np.mean([c["FP"] for c in cms])), 1),
            "TN": round(float(np.mean([c["TN"] for c in cms])), 1),
            "FN": round(float(np.mean([c["FN"] for c in cms])), 1),
        }

    # Paired comparisons: Hybrid vs Isolation Forest
    paired_comp: dict[str, Any] = {}
    for k in ["f1_score", "precision", "recall", "pr_auc", "roc_auc"]:
        diffs = np.array(collected["hybrid_full"][k]) - np.array(collected["anomaly_only"][k])
        # Paired t-test
        t_stat, p_val = stats.ttest_rel(collected["hybrid_full"][k], collected["anomaly_only"][k])
        # Wilcoxon signed-rank test
        try:
            w_stat, w_pval = stats.wilcoxon(diffs)
        except Exception:
            w_stat, w_pval = 0.0, 1.0

        paired_comp[k] = {
            "mean_difference": round(float(np.mean(diffs)), 4),
            "t_statistic": round(float(t_stat), 4) if not np.isnan(t_stat) else 0.0,
            "p_value": round(float(p_val), 5) if not np.isnan(p_val) else 1.0,
            "wilcoxon_p_value": round(float(w_pval), 5),
            "statistically_significant_p05": bool(p_val < 0.05) if not np.isnan(p_val) else False,
        }

    # Typology recall summary
    typ_summary: dict[str, Any] = {}
    for typ, d in typology_recalls.items():
        typ_summary[typ] = {
            det: {
                "mean": round(float(np.mean(d[det])), 4),
                "std": round(float(np.std(d[det], ddof=1)), 4) if len(d[det]) > 1 else 0.0,
            }
            for det in ["rules", "anomaly", "graph", "hybrid"]
        }

    return {
        "seeds_evaluated": seeds,
        "sample_count": len(seeds),
        "metrics_summary": summary,
        "average_confusion_matrices": avg_cms,
        "paired_comparison_hybrid_vs_if": paired_comp,
        "typology_recall_summary": typ_summary,
    }

if __name__ == "__main__":
    res = run_multi_seed()
    out_path = ROOT_DIR / "reports" / "multi_seed_evaluation.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    print("Multi-seed evaluation complete. Results saved to:", out_path)
