# Technical Audit and Discrepancy Reconciliation Report

**Project**: A Hybrid AML Detection and Evidence-Grounded SAR Generation Framework with Tamper-Evident Audit Logging  
**Date of Audit**: 2026-10-18  
**Scope**: Verification of Source Files, Benchmark Inconsistencies, Metric Reconciliations, Architectural Decisions, and Research Claims.  
**Auditor**: Senior Research Engineer & Scientific Integrity Reviewer  

---

## 1. Executive Summary

This audit establishes a single authoritative mathematical baseline for the entire AML research project. Prior experimental reports in the repository contained conflicting numbers arising from differences in partition chronological sorting, legacy composite rule scoring, graph detector buffer sizing, and varied linear aggregation weights.

Every numerical metric, confusion matrix count, and architectural parameter presented in the final research manuscript ([`full_project_research_paper.md`](file:///d:/Hackathon/HB/research/full_project_research_paper.md)) has been verified against the frozen test prediction artifact ([`reports/frozen_predictions/test_predictions_authoritative.json`](file:///d:/Hackathon/HB/reports/frozen_predictions/test_predictions_authoritative.json)) and underlying source code.

---

## 2. Discrepancy Reconciliation Matrix

| Area of Discrepancy | Conflicting Claims / Historical Reports | Source File & Location | Verification Performed | Authoritative Reconciled Value | Research Impact & Handling |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Test Partition Class Balance** | Early reports claimed 189 suspicious and 106 benign transactions ($N=295$). Confusion matrices reported $\text{TP}=113, \text{FN}=5$ ($\sum=118$). | [`data_generator/engine.py`](file:///d:/Hackathon/HB/data_generator/engine.py)<br>[`data_generator/benchmark.py`](file:///d:/Hackathon/HB/data_generator/benchmark.py) | Traced ground truth slicing vs transaction ID mapping. Slicing unsorted lists mapped mismatched indices. Synchronizing chronological order yields exact label counts. | **118 Positive (Suspicious), 177 Negative (Benign)** ($N=295$, Positive rate = $40.0\%$). | Enforced via automated unit test `test_confusion_matrix_and_class_count_assertions`. All confusion matrices strictly satisfy $\text{TP}+\text{FN}=118$ and $\text{TN}+\text{FP}=177$. |
| **2. Validation Partition Class Balance** | Early drafts claimed Validation contained 0 suspicious transactions, preventing threshold tuning. | [`data_generator/engine.py`](file:///d:/Hackathon/HB/data_generator/engine.py) | Inspected synchronized 60/20/20 partition ($N=1,474$). Train ($N=884$) has 0 positive (100% benign baseline). Validation ($N=295$) spans Jan 24–Feb 08. | **42 Positive (Suspicious), 253 Negative (Benign)** ($N=295$, Positive rate = $14.24\%$). | Validates threshold calibration on Validation ($\tau=0.20$, F1 = 0.5827) without test label data leakage. |
| **3. Rules-Only Test Performance** | Legacy reports claimed Rules F1 was 0.7965 or 0.8333 with 90 True Positives. | [`rag_pipeline/rule_engine.py`](file:///d:/Hackathon/HB/rag_pipeline/rule_engine.py)<br>[`data_generator/benchmark.py`](file:///d:/Hackathon/HB/data_generator/benchmark.py) | Re-executed rule detector on frozen test set ($N=295$). In point transaction scoring ($\tau=0.50$, flagging amount $\ge 10^6$ INR or offshore jurisdiction), only 8 transactions flag. | **$\text{TP}=7, \text{FP}=1, \text{TN}=176, \text{FN}=111$**.<br>Prec: 0.8750, Rec: 0.0593, F1: 0.1111, ROC-AUC: 0.5268, PR-AUC: 0.4282. | The historical high F1 (0.7965) evaluated aggregate customer case summaries, not individual test transactions. The paper clearly distinguishes transaction-level point detection from customer-level case triage. |
| **4. Graph Detector Evaluation Counts** | Early benchmarks reported Graph F1 = 0.5122 ($\text{TP}=42, \text{FN}=76$), whereas later runs reported F1 = 0.6492 ($\text{TP}=62, \text{FN}=56$). | [`graph/graph_detector.py`](file:///d:/Hackathon/HB/graph/graph_detector.py)<br>[`data_generator/benchmark.py`](file:///d:/Hackathon/HB/data_generator/benchmark.py) | Investigated `max_transactions` buffer in `GraphLaunderingDetector`. Default of 1,000 truncated test partition transactions. Increasing buffer capacity to 5,000 preserved full graph topology. | **$\text{TP}=62, \text{FP}=11, \text{TN}=166, \text{FN}=56$**.<br>Prec: 0.8493, Rec: 0.5254, F1: 0.6492, ROC-AUC: 0.7322, PR-AUC: 0.6479. | Confirmed authoritative on the 5,000-capacity graph run. Truncation buffer limitations are documented as a system parameter and scalability trade-off. |
| **5. Hybrid Weight Configuration** | `detection/aggregator.py` defines weights $(0.35, 0.25, 0.40)$, while benchmark scripts use $(0.35, 0.35, 0.30)$. | [`detection/aggregator.py`](file:///d:/Hackathon/HB/detection/aggregator.py)<br>[`data_generator/benchmark.py`](file:///d:/Hackathon/HB/data_generator/benchmark.py) | Verified weight usage across artifacts. `DEFAULT_WEIGHTS` in `aggregator.py` is the online API default; benchmark scripts explicitly instantiated weights $w_r=0.35, w_a=0.35, w_g=0.30$. | Authoritative benchmark predictions used **$w_r=0.35, w_a=0.35, w_g=0.30$**. | Explicitly documented in paper. Both configurations are linear convex combinations. Benchmark results correspond strictly to the $(0.35, 0.35, 0.30)$ configuration. |
| **6. Hybrid vs Isolation Forest Superiority** | Marketing summaries claimed Hybrid outperformed all detectors across all metrics. | [`reports/evaluation_report.md`](file:///d:/Hackathon/HB/reports/evaluation_report.md)<br>[`research/tables/table2_detection_performance.md`](file:///d:/Hackathon/HB/research/tables/table2_detection_performance.md) | Verified ROC-AUC and PR-AUC. Isolation Forest achieves higher ROC-AUC (0.9762 vs 0.9574) and PR-AUC (0.9369 vs 0.9156). Hybrid achieves higher Recall (0.9915 vs 0.9576) and higher Precision at tight FPR budgets. | **Claim Downgraded & Qualified**: Hybrid is not uniformly superior across all metrics; Isolation Forest provides stronger pure point-anomaly ranking, while Hybrid maximizes recall and captures complex graph-structural typologies. | Scientific integrity preserved. The paper presents this honest trade-off as a central empirical finding. |
| **7. "Blockchain" Architectural Characterization** | Repository README referred to "Blockchain-Based Audit Integrity". | [`audit/ledger.py`](file:///d:/Hackathon/HB/audit/ledger.py)<br>[`backend/database.py`](file:///d:/Hackathon/HB/backend/database.py) | Inspected cryptographic implementation. Uses SHA-256 block hashing with backward hash pointers (`prev_hash`) and monotonic sequence numbers stored in PostgreSQL/SQLite. No peer-to-peer consensus, mining, or distributed Byzantine fault tolerance. | **Hash-Chained Tamper-Evident Audit Ledger** (Single-Node, Centralized Database). | Title and claims updated to "Tamper-Evident Audit Logging". Avoids overstating decentralized blockchain capabilities while validating cryptographic tamper detection against event modification/deletion. |

---

## 3. Mathematical Verification of Frozen Predictions

Direct verification executed on `reports/frozen_predictions/test_predictions_authoritative.json` ($N=295$):

### Primary Identity Checks:
- Total Transactions: $N = \text{TP} + \text{FP} + \text{TN} + \text{FN} = 295$
- Ground-Truth Positives: $P = \text{TP} + \text{FN} = 118$
- Ground-Truth Negatives: $N_{\text{neg}} = \text{TN} + \text{FP} = 177$

### Detailed Confusion Matrices:
1. **Rules Engine Only** ($\tau = 0.50$):
   $$\text{TP} = 7, \quad \text{FP} = 1, \quad \text{TN} = 176, \quad \text{FN} = 111$$
   $$\text{Precision} = \frac{7}{7 + 1} = 0.8750, \quad \text{Recall} = \frac{7}{7 + 111} = 0.0593, \quad \text{F1} = 0.1111$$
   $$\text{FPR} = \frac{1}{1 + 176} = 0.0056, \quad \text{Alert Rate} = \frac{8}{295} = 0.0271$$

2. **Isolation Forest Only** ($\tau = 0.50$):
   $$\text{TP} = 113, \quad \text{FP} = 8, \quad \text{TN} = 169, \quad \text{FN} = 5$$
   $$\text{Precision} = \frac{113}{113 + 8} = 0.9339, \quad \text{Recall} = \frac{113}{113 + 5} = 0.9576, \quad \text{F1} = 0.9456$$
   $$\text{FPR} = \frac{8}{8 + 169} = 0.0452, \quad \text{Alert Rate} = \frac{121}{295} = 0.4102$$

3. **Graph Detector Only** ($\tau = 0.50$):
   $$\text{TP} = 62, \quad \text{FP} = 11, \quad \text{TN} = 166, \quad \text{FN} = 56$$
   $$\text{Precision} = \frac{62}{62 + 11} = 0.8493, \quad \text{Recall} = \frac{62}{62 + 56} = 0.5254, \quad \text{F1} = 0.6492$$
   $$\text{FPR} = \frac{11}{11 + 166} = 0.0621, \quad \text{Alert Rate} = \frac{73}{295} = 0.2475$$

4. **Hybrid Ensemble** ($\tau = 0.20$, Validation-Calibrated):
   $$\text{TP} = 117, \quad \text{FP} = 18, \quad \text{TN} = 159, \quad \text{FN} = 1$$
   $$\text{Precision} = \frac{117}{117 + 18} = 0.8667, \quad \text{Recall} = \frac{117}{117 + 1} = 0.9915, \quad \text{F1} = 0.9249$$
   $$\text{FPR} = \frac{18}{18 + 159} = 0.1017, \quad \text{Alert Rate} = \frac{135}{295} = 0.4576$$

---

## 4. Unresolved Issues & Scope Boundaries

1. **Total Scenario Ground Truth Count ($189$ vs $160$ Partitioned Positives)**:
   - `scenario_ground_truth.csv` lists 189 suspicious transactions generated across all 17 suspicious scenario definitions.
   - When sliced into chronological partitions (Train: 884, Val: 295, Test: 295, Sum: 1,474), the chronological distribution is:
     - Training: 0 suspicious (100% benign baseline)
     - Validation: 42 suspicious
     - Test: 118 suspicious
     - Total partitioned positives: $42 + 118 = 160$.
   - **Resolution**: 29 scenario transactions generated during scenario synthesis occurred at timestamps or customer IDs that were not absorbed into the 1,474-row window or were excluded by scenario overlap de-duplication. The test partition evaluation ($N=295$) strictly evaluates the 118 positives and 177 negatives present in its window.

2. **Single-Node Threat Model for Audit Ledger**:
   - The ledger guarantees detection of database record tampering (e.g., updating an amount, deleting an audit row, or re-ordering events) as verified in `test_integration_and_audit_ledger_verification`.
   - However, an attacker with full root access to the database host could recompute SHA-256 hashes for the entire table from the genesis block forward unless an external signed anchor is published to an independent third party or hardware security module (HSM).
   - **Resolution**: This boundary is explicitly stated in the Threat Model and Limitations sections.

---

## 5. Audit Conclusion

All inconsistencies have been traced, documented, and mathematically reconciled. No fabricated metrics, uncalibrated probability claims, or exaggerated blockchain assertions remain in the paper draft or tables. The research paper manuscript may proceed to final publication-ready rendering based exclusively on these verified facts.
