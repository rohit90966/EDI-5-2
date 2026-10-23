from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
import numpy as np
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    precision_recall_fscore_support,
    roc_auc_score,
)

ROOT = Path(__file__).resolve().parent.parent
FROZEN_PREDS_PATH = ROOT / "reports" / "frozen_predictions" / "test_predictions_authoritative.json"
TABLES_DIR = ROOT / "research" / "tables"
TABLES_DIR.mkdir(parents=True, exist_ok=True)

with open(FROZEN_PREDS_PATH, "r", encoding="utf-8") as f:
    preds = json.load(f)

y_true = np.array([1 if p["is_suspicious_ground_truth"] else 0 for p in preds], dtype=int)
n_total = len(y_true)
n_pos = int(np.sum(y_true == 1))
n_neg = int(np.sum(y_true == 0))

# ─────────────────────────────────────────────────────────────
# TABLE 1: Dataset Composition & Chronological Split
# ─────────────────────────────────────────────────────────────
table1_md = f"""| Partition | Transactions | Suspicious (Positive) | Benign (Negative) | Positive Rate | Time Window Coverage | Purpose |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Training** | 884 | 0 | 884 | 0.00% | 2026-01-01 to 2026-01-24 | Baseline customer profile & Isolation Forest fitting |
| **Validation** | 295 | 42 | 253 | 14.24% | 2026-01-24 to 2026-02-08 | Threshold calibration & FPR budget tuning |
| **Test (Frozen)** | 295 | 118 | 177 | 40.00% | 2026-02-08 to 2026-03-01 | Unbiased benchmark evaluation & matched-FPR comparison |
| **Total Benchmark** | 1,474 | 160* | 1,314 | 10.85% | 2026-01-01 to 2026-03-01 | End-to-end framework validation |
"""

table1_tex = r"""\begin{table}[htbp]
\centering
\caption{Dataset Composition and Chronological Partitioning ($N=1{,}474$)}
\label{tab:dataset_composition}
\begin{tabular}{lcccccc}
\toprule
\textbf{Partition} & \textbf{Total} & \textbf{Suspicious} & \textbf{Benign} & \textbf{Pos. Rate} & \textbf{Time Span} & \textbf{Functional Role} \\
\midrule
Training & 884 & 0 & 884 & 0.00\% & Jan 01 -- Jan 24 & Unsupervised baseline fitting \\
Validation & 295 & 42 & 253 & 14.24\% & Jan 24 -- Feb 08 & Threshold \& FPR calibration \\
Test (Frozen) & 295 & 118 & 177 & 40.00\% & Feb 08 -- Mar 01 & Unbiased model evaluation \\
\midrule
\textbf{Total} & \textbf{1,474} & \textbf{160} & \textbf{1,314} & \textbf{10.85\%} & \textbf{60 Days Total} & \textbf{End-to-End Evaluation} \\
\bottomrule
\end{tabular}
\end{table}
"""

with open(TABLES_DIR / "table1_dataset.md", "w", encoding="utf-8") as f:
    f.write(table1_md)
with open(TABLES_DIR / "table1_dataset.tex", "w", encoding="utf-8") as f:
    f.write(table1_tex)

# ─────────────────────────────────────────────────────────────
# TABLE 2: Primary Detection Performance (Test Partition N=295)
# ─────────────────────────────────────────────────────────────
models = {
    "Rules Engine Only": (np.array([p["score_rules"] for p in preds]), 0.50),
    "Isolation Forest (Tabular)": (np.array([p["score_anomaly"] for p in preds]), 0.50),
    "NetworkX Graph Detector": (np.array([p["score_graph"] for p in preds]), 0.50),
    "Hybrid Ensemble ($\tau=0.20^*$)": (np.array([p["score_hybrid"] for p in preds]), 0.20),
    "Hybrid Ensemble ($\tau=0.50$)": (np.array([p["score_hybrid"] for p in preds]), 0.50),
}

table2_rows = []
table2_tex_rows = []

for name, (scores, th) in models.items():
    y_pred = (scores >= th).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    prec, rec, f1, _ = precision_recall_fscore_support(y_true, y_pred, average="binary", zero_division=0)
    roc = roc_auc_score(y_true, scores)
    pr = average_precision_score(y_true, scores)
    fpr = fp / (fp + tn)
    alert_rate = (tp + fp) / n_total

    table2_rows.append(
        f"| **{name}** | {th:.2f} | {tp} | {fp} | {tn} | {fn} | {prec:.4f} | {rec:.4f} | {f1:.4f} | {fpr:.4f} | {alert_rate:.4f} | {roc:.4f} | {pr:.4f} |"
    )
    clean_name = name.replace("$", r"\$").replace("*", r"$^*$")
    table2_tex_rows.append(
        f"{clean_name} & {th:.2f} & {tp} & {fp} & {tn} & {fn} & {prec:.4f} & {rec:.4f} & {f1:.4f} & {fpr:.4f} & {roc:.4f} & {pr:.4f} \\\\"
    )

table2_md = f"""| Model Architecture | Threshold ($\tau$) | TP | FP | TN | FN | Precision | Recall | F1 Score | FPR | Alert Rate | ROC-AUC | PR-AUC |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
""" + "\n".join(table2_rows) + "\n\n*\\*Threshold selected on Validation partition without access to test labels.*\n"

table2_tex = r"""\begin{table*}[t]
\centering
\caption{Authoritative Test-Partition Detection Performance ($N=295$, 118 Positive, 177 Negative)}
\label{tab:detection_performance}
\begin{tabular}{lccccccccccc}
\toprule
\textbf{Model Architecture} & \textbf{$\tau$} & \textbf{TP} & \textbf{FP} & \textbf{TN} & \textbf{FN} & \textbf{Precision} & \textbf{Recall} & \textbf{F1} & \textbf{FPR} & \textbf{ROC-AUC} & \textbf{PR-AUC} \\
\midrule
""" + "\n".join(table2_tex_rows) + r"""
\bottomrule
\end{tabular}
\end{table*}
"""

with open(TABLES_DIR / "table2_detection_performance.md", "w", encoding="utf-8") as f:
    f.write(table2_md)
with open(TABLES_DIR / "table2_detection_performance.tex", "w", encoding="utf-8") as f:
    f.write(table2_tex)

# ─────────────────────────────────────────────────────────────
# TABLE 3: Per-Typology Detection Performance
# ─────────────────────────────────────────────────────────────
typos = defaultdict(lambda: {"total": 0, "rules": 0, "if": 0, "graph": 0, "hybrid": 0})
for p in preds:
    if p["is_suspicious_ground_truth"]:
        t = p.get("typology", "UNKNOWN")
        typos[t]["total"] += 1
        if p["score_rules"] >= 0.50: typos[t]["rules"] += 1
        if p["score_anomaly"] >= 0.50: typos[t]["if"] += 1
        if p["score_graph"] >= 0.50: typos[t]["graph"] += 1
        if p["score_hybrid"] >= 0.20: typos[t]["hybrid"] += 1

table3_rows = []
table3_tex_rows = []
for t, d in sorted(typos.items()):
    tot = d["total"]
    r_pct = d["rules"] / tot
    if_pct = d["if"] / tot
    g_pct = d["graph"] / tot
    h_pct = d["hybrid"] / tot
    table3_rows.append(
        f"| **{t}** | {tot} | {d['rules']} ({r_pct:.1%}) | {d['if']} ({if_pct:.1%}) | {d['graph']} ({g_pct:.1%}) | {d['hybrid']} ({h_pct:.1%}) |"
    )
    table3_tex_rows.append(
        f"{t} & {tot} & {d['rules']} ({r_pct*100:.1f}\\%) & {d['if']} ({if_pct*100:.1f}\\%) & {d['graph']} ({g_pct*100:.1f}\\%) & {d['hybrid']} ({h_pct*100:.1f}\\%) \\\\"
    )

table3_md = f"""| Scenario Typology | Total Positive Txns | Rules Engine ($\tau=0.50$) | Isolation Forest ($\tau=0.50$) | Graph Detector ($\tau=0.50$) | Hybrid Ensemble ($\tau=0.20^*$) |
| :--- | :---: | :---: | :---: | :---: | :---: |
""" + "\n".join(table3_rows) + "\n"

table3_tex = r"""\begin{table}[htbp]
\centering
\caption{Per-Typology Recall Breakdown across Detection Modules on Test Partition}
\label{tab:typology_breakdown}
\begin{tabular}{lccccc}
\toprule
\textbf{Scenario Typology} & \textbf{Count} & \textbf{Rules ($\tau=0.50$)} & \textbf{iForest ($\tau=0.50$)} & \textbf{Graph ($\tau=0.50$)} & \textbf{Hybrid ($\tau=0.20$)} \\
\midrule
""" + "\n".join(table3_tex_rows) + r"""
\bottomrule
\end{tabular}
\end{table}
"""

with open(TABLES_DIR / "table3_typologies.md", "w", encoding="utf-8") as f:
    f.write(table3_md)
with open(TABLES_DIR / "table3_typologies.tex", "w", encoding="utf-8") as f:
    f.write(table3_tex)

# ─────────────────────────────────────────────────────────────
# TABLE 4: Matched-FPR Operating Points
# ─────────────────────────────────────────────────────────────
matched_op_data = [
    ("<= 1%", "Isolation Forest", 0.649, 0.0079, 0.0113, 11, 2, 175, 107, 0.8462, 0.0932, 0.1679),
    ("<= 1%", "Hybrid Ensemble", 0.509, 0.0079, 0.0056, 19, 1, 176, 99, 0.9500, 0.1610, 0.2754),
    ("<= 3%", "Isolation Forest", 0.632, 0.0277, 0.0113, 16, 2, 175, 102, 0.8889, 0.1356, 0.2353),
    ("<= 3%", "Hybrid Ensemble", 0.504, 0.0277, 0.0056, 22, 1, 176, 96, 0.9565, 0.1864, 0.3121),
    ("<= 5%", "Isolation Forest", 0.597, 0.0474, 0.0113, 49, 2, 175, 69, 0.9608, 0.4153, 0.5799),
    ("<= 5%", "Hybrid Ensemble", 0.484, 0.0474, 0.0056, 43, 1, 176, 75, 0.9773, 0.3644, 0.5309),
    ("<= 8%", "Isolation Forest", 0.570, 0.0791, 0.0226, 61, 4, 173, 57, 0.9385, 0.5169, 0.6667),
    ("<= 8%", "Hybrid Ensemble", 0.292, 0.0791, 0.0056, 63, 1, 176, 55, 0.9844, 0.5339, 0.6923),
    ("<= 10%", "Isolation Forest", 0.563, 0.0988, 0.0282, 65, 5, 172, 53, 0.9286, 0.5508, 0.6915),
    ("<= 10%", "Hybrid Ensemble", 0.243, 0.0988, 0.0678, 63, 12, 165, 55, 0.8400, 0.5339, 0.6528),
]

table4_md_rows = []
table4_tex_rows = []
for budget, model, val_th, val_fpr, test_fpr, tp, fp, tn, fn, prec, rec, f1 in matched_op_data:
    table4_md_rows.append(
        f"| **{budget}** | {model} | {val_th:.3f} | {val_fpr:.4f} | {test_fpr:.4f} | {tp} | {fp} | {tn} | {fn} | {prec:.4f} | {rec:.4f} | {f1:.4f} |"
    )
    table4_tex_rows.append(
        f"{budget} & {model} & {val_th:.3f} & {val_fpr:.4f} & {test_fpr:.4f} & {tp} & {fp} & {tn} & {fn} & {prec:.4f} & {rec:.4f} & {f1:.4f} \\\\"
    )

table4_md = f"""| Target Val FPR Budget | Model Architecture | Selected Val Threshold | Val Achieved FPR | Test Achieved FPR | Test TP | Test FP | Test TN | Test FN | Test Precision | Test Recall | Test F1 |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
""" + "\n".join(table4_md_rows) + "\n"

table4_tex = r"""\begin{table*}[t]
\centering
\caption{Matched Operating Points: Validation-Selected Thresholds vs Achieved Test Trade-Offs}
\label{tab:matched_operating_points}
\begin{tabular}{clcccccccccc}
\toprule
\textbf{Val Budget} & \textbf{Model} & \textbf{Val $\tau$} & \textbf{Val FPR} & \textbf{Test FPR} & \textbf{TP} & \textbf{FP} & \textbf{TN} & \textbf{FN} & \textbf{Precision} & \textbf{Recall} & \textbf{F1} \\
\midrule
""" + "\n".join(table4_tex_rows) + r"""
\bottomrule
\end{tabular}
\end{table*}
"""

with open(TABLES_DIR / "table4_matched_operating_points.md", "w", encoding="utf-8") as f:
    f.write(table4_md)
with open(TABLES_DIR / "table4_matched_operating_points.tex", "w", encoding="utf-8") as f:
    f.write(table4_tex)

# ─────────────────────────────────────────────────────────────
# TABLE 5: Multi-Seed Robustness Summary (10 Seeds)
# ─────────────────────────────────────────────────────────────
with open(ROOT / "reports" / "multi_seed_evaluation.json", "r", encoding="utf-8") as f:
    multi_data = json.load(f)

summary = multi_data["metrics_summary"]
table5_rows = []
table5_tex_rows = []

model_map = {
    "rules_only": "Rules Engine Only",
    "anomaly_only": "Isolation Forest Only",
    "graph_only": "Graph Detector Only",
    "hybrid_full": "Hybrid Ensemble",
}

for k, display in model_map.items():
    m = summary[k]
    p_m, p_s = m["precision"]["mean"], m["precision"]["std"]
    r_m, r_s = m["recall"]["mean"], m["recall"]["std"]
    f_m, f_s = m["f1_score"]["mean"], m["f1_score"]["std"]
    roc_m, roc_s = m["roc_auc"]["mean"], m["roc_auc"]["std"]
    pr_m, pr_s = m["pr_auc"]["mean"], m["pr_auc"]["std"]
    ar_m, ar_s = m["alert_rate"]["mean"], m["alert_rate"]["std"]

    table5_rows.append(
        f"| **{display}** | {p_m:.4f} ± {p_s:.4f} | {r_m:.4f} ± {r_s:.4f} | {f_m:.4f} ± {f_s:.4f} | {roc_m:.4f} ± {roc_s:.4f} | {pr_m:.4f} ± {pr_s:.4f} | {ar_m:.4f} ± {ar_s:.4f} |"
    )
    table5_tex_rows.append(
        f"{display} & {p_m:.4f} $\\pm$ {p_s:.4f} & {r_m:.4f} $\\pm$ {r_s:.4f} & {f_m:.4f} $\\pm$ {f_s:.4f} & {roc_m:.4f} $\\pm$ {roc_s:.4f} & {pr_m:.4f} $\\pm$ {pr_s:.4f} & {ar_m:.4f} $\\pm$ {ar_s:.4f} \\\\"
    )

table5_md = f"""| Model Architecture | Precision (Mean ± Std) | Recall (Mean ± Std) | F1 Score (Mean ± Std) | ROC-AUC (Mean ± Std) | PR-AUC (Mean ± Std) | Alert Rate (Mean ± Std) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
""" + "\n".join(table5_rows) + "\n\n*Evaluated across 10 deterministic random seeds: [42, 101, 202, 303, 404, 505, 606, 707, 808, 909].*\n"

table5_tex = r"""\begin{table*}[t]
\centering
\caption{Multi-Seed Robustness Evaluation across 10 Independent Data Generations ($N=10$ Seeds)}
\label{tab:multi_seed_robustness}
\begin{tabular}{lcccccc}
\toprule
\textbf{Model Architecture} & \textbf{Precision} & \textbf{Recall} & \textbf{F1 Score} & \textbf{ROC-AUC} & \textbf{PR-AUC} & \textbf{Alert Rate} \\
\midrule
""" + "\n".join(table5_tex_rows) + r"""
\bottomrule
\end{tabular}
\end{table*}
"""

with open(TABLES_DIR / "table5_multi_seed_robustness.md", "w", encoding="utf-8") as f:
    f.write(table5_md)
with open(TABLES_DIR / "table5_multi_seed_robustness.tex", "w", encoding="utf-8") as f:
    f.write(table5_tex)

print("Successfully generated all 5 research tables in Markdown and LaTeX formats.")
