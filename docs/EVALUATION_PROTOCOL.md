# AML Multi-Detector Evaluation Protocol & Research Methodology

**Author:** Principal ML Researcher & AML Systems Engineer  
**Harness Module:** `evaluation/evaluator.py`, `scripts/run_evaluation.py`  
**Output Artifacts:** `reports/evaluation_report.json`, `reports/evaluation_report.md`  

---

## 1. Evaluation Objectives

1. Quantify the individual detection efficacy and computational latency of:
   - **Layer A:** Deterministic AML Rules Engine
   - **Layer B:** Unsupervised Behavioral Isolation Forest
   - **Layer C:** Directed Network MultiGraph Detector
2. Measure the ablation impact of combining detection layers to assess whether the proposed **Hybrid Architecture** delivers superior Precision, Recall, and PR-AUC over standalone detectors.
3. Validate temporal integrity and verify complete absence of data leakage.

---

## 2. Dataset Synthesis & Typology Design

The evaluation harness uses a deterministic synthetic data generator (`evaluation/synthetic_generator.py`, random seed `42`) to simulate a realistic banking stream:

- **Total Sample Size:** 283 transactions across 20 distinct normal customer accounts and 5 targeted test accounts.
- **Background Normal Traffic:** 245 routine consumer transactions (salaries, utility bills, groceries, peer transfers) modeled with realistic Poisson arrival intervals and log-normal amount distributions.
- **Benign Controls:**
  - One-time legitimate corporate bonus and mutual fund investment (`BENIGN_BONUS`, `BENIGN_INVEST`).
  - High-velocity legitimate e-commerce merchant settlements (`BENIGN_MERCHANT`).
- **Targeted Laundering Motifs (38 instances, 13.4% prevalence):**
  1. **Structuring / Smurfing (`STRUCTURING`):** 22 repeated transactions just beneath statutory reporting thresholds (INR 48,000–49,500) over 3 days across multiple branch codes.
  2. **Rapid Pass-Through (`PASS_THROUGH`):** Large inward credit followed immediately by outward wire dissipation to a high-risk jurisdiction (UAE) within 6 hours.
  3. **Circular Funds Flow (`CIRCULAR_FLOW`):** Closed cycle $A \to B \to C \to D \to A$ with minor fee degradation within 24 hours.
  4. **Fan-In / Fan-Out (`FAN_IN_FAN_OUT`):** 5 distinct victim accounts converging on a money mule aggregation hub, followed by 5 outbound dispersals.

---

## 3. Metrics & Scoring Criteria

Because money laundering is inherently a severe class-imbalance problem, evaluating solely with ROC-AUC is misleading. The protocol emphasizes:

- **Precision-Recall AUC (PR-AUC / Average Precision):** The primary indicator of detection quality under class imbalance.
- **Precision, Recall, and F1-Score:** Evaluated at calibrated policy decision thresholds.
- **Alert Rate / False Positive Rate:** Percentage of total transactions escalated to human compliance analysts (capacity-constrained).
- **Per-Typology Recall:** Detection sensitivity broken down across each distinct laundering pattern.
- **Execution Latency (ms):** Runtime required to process transactions and construct graphs.

---

## 4. Leakage Prevention Protocol

The test harness enforces an automated pre-flight assertion `perform_leakage_check()`:
1. Verifies that no ground-truth attributes (`is_suspicious`, `typology`, `label`) exist in transaction feature dictionaries.
2. Asserts that feature calculations strictly respect the as-of timestamp $\le t_0$, guaranteeing that transactions occurring after the target event cannot artificially influence historical rolling statistics.

---

## 5. Ablation Study Results Summary

| Configuration | F1-Score | PR-AUC | Key Behavior |
|---|---|---|---|
| **Rules Only** | `0.7937` | `0.7038` | Catches 100% of structuring, but completely blind to circular cycles (0% recall). |
| **Isolation Forest Only** | `0.2264` | `0.1762` | High outlier detection on large bonus controls; weak on small structuring txns. |
| **Graph Network Only** | `0.1463` | `0.1167` | 100% recall on circular flows and pass-throughs, but misses single-account velocity. |
| **Full Hybrid (Proposed)** | `0.3137`* | `0.2933` | Highest multi-typology coverage with lowest uncorroborated alert rate (4.59%). |

*Note: In production tuning, threshold calibration on validation splits optimizes the trade-off between analyst capacity and risk tolerance.*

---

## 6. How to Reproduce Evaluation

Execute the evaluation harness directly:
```bash
.venv\Scripts\python.exe scripts/run_evaluation.py
```
Outputs:
- Machine-readable JSON: `reports/evaluation_report.json`
- Human-readable Markdown: `reports/evaluation_report.md`
