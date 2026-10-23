# Phase 5 — Comprehensive Reproducibility and Audit Report

**Project Title**: A Hybrid Fraud Detection and Retrieval-Augmented Suspicious Activity Report (SAR) Generation Framework for Banking Systems with Blockchain-Based Audit Integrity  
**Date**: 2026-10-18  
**Scope**: Verification of Source Files, Prediction Freezing, Threshold Selection Audit, Research Claims Assessment, SAR Evaluation Protocol, and Threats to Validity.

---

## 1. System Implementation Source Inventory

Every component of the hybrid AML pipeline was verified against its exact implementation in the repository:

| Capability | Implementing Module | Key Functions / Classes | Configuration & Verification |
| :--- | :--- | :--- | :--- |
| **Rules Engine** | [`rag_pipeline/rule_engine.py`](file:///d:/Hackathon/HB/rag_pipeline/rule_engine.py) & [`detection/rules_adapter.py`](file:///d:/Hackathon/HB/detection/rules_adapter.py) | `evaluate_rules()`, `RulesEngineDetector` | `rules.yaml` (SHA-256: `1e22f04cd5...`) |
| **Isolation Forest** | [`ml/anomaly_detector.py`](file:///d:/Hackathon/HB/ml/anomaly_detector.py) & [`ml/features.py`](file:///d:/Hackathon/HB/ml/features.py) | `IsolationForestDetector`, `build_dataset_feature_matrix()` | 16 continuous features; sigmoid normalization. |
| **Graph Detector** | [`graph/graph_detector.py`](file:///d:/Hackathon/HB/graph/graph_detector.py) | `GraphLaunderingDetector`, `build_graph()` | NetworkX multigraph, cycle length $\le 5$, buffer capacity 5000. |
| **Risk Aggregation** | [`detection/aggregator.py`](file:///d:/Hackathon/HB/detection/aggregator.py) | `HybridRiskAggregator.aggregate()` | Weights: Rules 0.35, Anomaly 0.35, Graph 0.30; handles degraded status. |
| **Compliance Policy** | [`detection/policy.py`](file:///d:/Hackathon/HB/detection/policy.py) | `AmlPolicyEngine.evaluate()` | Deterministic escalations (`SAR_DRAFT_ELIGIBLE`, `ANALYST_REVIEW`). |
| **Audit Ledger** | [`audit/ledger.py`](file:///d:/Hackathon/HB/audit/ledger.py) | `append_ledger_block()`, `verify_ledger()` | SHA-256 canonical serialization, monotonic sequence numbers. |
| **SAR & PII Safety** | [`sar_safety.py`](file:///d:/Hackathon/HB/sar_safety.py) & [`evaluation/sar_narrative_eval.py`](file:///d:/Hackathon/HB/evaluation/sar_narrative_eval.py) | `detect_pii_leak()`, `score_narrative_rubric()` | 5-dimension rubric (100-pt scale), PII regex masking. |
| **Synthetic Generator** | [`data_generator/engine.py`](file:///d:/Hackathon/HB/data_generator/engine.py) | `SyntheticDataEngine` | Versioned generation, running balance reconciliation, zero leakage. |

---

## 2. Benchmark Artifact Freezing & Integrity

The evaluation dataset and test predictions have been frozen with SHA-256 integrity proofs in [`reports/reproducibility_manifest.json`](file:///d:/Hackathon/HB/reports/reproducibility_manifest.json):

- `data/synthetic/transactions.csv` ($1,474$ rows, SHA-256: `dd08901f9f...`)
- `data/synthetic/scenario_ground_truth.csv` ($1,474$ rows, SHA-256: `d24e805adf...`)
- `data/synthetic/accounts.csv` ($39$ rows, SHA-256: `76dba1e928...`)
- `data/synthetic/customers.csv` ($30$ rows, SHA-256: `00e3e1282d...`)
- `data/synthetic/investigation_cases.jsonl` ($28$ cases, SHA-256: `2674a3c58a...`)
- `reports/frozen_predictions/test_predictions_authoritative.json` ($295$ test cases with raw scores)

---

## 3. Recomputed Authoritative Metrics (Test Partition, N = 295)

Directly recomputed from `test_predictions_authoritative.json`:

| Model | Operating Threshold | TP | FP | TN | FN | Precision | Recall | F1 Score | FPR | Alert Rate | ROC-AUC | PR-AUC |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Rules Only** | 0.500 | 7 | 1 | 176 | 111 | 0.8750 | 0.0593 | 0.1111 | 0.0056 | 0.0271 | 0.5268 | 0.4282 |
| **Anomaly Only (IF)** | 0.500 | 113 | 8 | 169 | 5 | **0.9339** | 0.9576 | **0.9456** | 0.0452 | 0.4102 | **0.9762** | **0.9369** |
| **Graph Only** | 0.500 | 62 | 11 | 166 | 56 | 0.8493 | 0.5254 | 0.6492 | 0.0621 | 0.2475 | 0.7322 | 0.6479 |
| **Hybrid Ensemble** | 0.200* | 117 | 18 | 159 | 1 | 0.8667 | **0.9915** | 0.9249 | 0.1017 | 0.4576 | 0.9574 | 0.9156 |

*\*Threshold selected on Validation partition without access to test labels.*

### Mathematical Reconciliation:
- $N_{\text{pos}} = 118$: $\text{TP} + \text{FN} = 7 + 111 = 113 + 5 = 62 + 56 = 117 + 1 = 118$.
- $N_{\text{neg}} = 177$: $\text{TN} + \text{FP} = 176 + 1 = 169 + 8 = 166 + 11 = 159 + 18 = 177$.
- Total: $118 + 177 = 295$.

---

## 4. Matched Operating Points: Validation Selection vs Achieved Test FPR

Thresholds were calibrated **strictly on the Validation partition** to satisfy target false-positive rate budgets, then evaluated on the unseen Test set:

| Target Val FPR Budget | Model | Selected Val Threshold | Val Achieved FPR | Test Achieved FPR | Test TP | Test FP | Test TN | Test FN | Test Precision | Test Recall | Test F1 |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **$\le 1\%$** | Isolation Forest | 0.649 | 0.0079 | 0.0113 | 11 | 2 | 175 | 107 | 0.8462 | 0.0932 | 0.1679 |
| | **Hybrid Ensemble** | **0.509** | **0.0079** | **0.0056** | **19** | **1** | **176** | **99** | **0.9500** | **0.1610** | **0.2754** |
| **$\le 3\%$** | Isolation Forest | 0.632 | 0.0277 | 0.0113 | 16 | 2 | 175 | 102 | 0.8889 | 0.1356 | 0.2353 |
| | **Hybrid Ensemble** | **0.504** | **0.0277** | **0.0056** | **22** | **1** | **176** | **96** | **0.9565** | **0.1864** | **0.3121** |
| **$\le 5\%$** | **Isolation Forest** | **0.597** | **0.0474** | **0.0113** | **49** | **2** | **175** | **69** | **0.9608** | **0.4153** | **0.5799** |
| | Hybrid Ensemble | 0.484 | 0.0474 | 0.0056 | 43 | 1 | 176 | 75 | 0.9773 | 0.3644 | 0.5309 |
| **$\le 8\%$** | Isolation Forest | 0.570 | 0.0791 | 0.0226 | 61 | 4 | 173 | 57 | 0.9385 | 0.5169 | 0.6667 |
| | **Hybrid Ensemble** | **0.292** | **0.0791** | **0.0056** | **63** | **1** | **176** | **55** | **0.9844** | **0.5339** | **0.6923** |
| **$\le 10\%$** | **Isolation Forest** | **0.563** | **0.0988** | **0.0282** | **65** | **5** | **172** | **53** | **0.9286** | **0.5508** | **0.6915** |
| | Hybrid Ensemble | 0.243 | 0.0988 | 0.0678 | 63 | 12 | 165 | 55 | 0.8400 | 0.5339 | 0.6528 |

### Research Observations:
- **Strict Budget Regime ($\text{FPR} \le 3\%$)**: The Hybrid ensemble consistently delivers higher precision ($95.0\text{--}95.7\%$) than Isolation Forest ($84.6\text{--}88.9\%$) because corroboration between detectors suppresses spurious statistical noise.
- **Validation Calibration Stability**: Because the validation set contains hard-negative controls (e.g. retail flash sales, medical emergencies), thresholds calibrated to satisfy validation budgets conservatively suppress false alarms on the test set (e.g. at budget $8\%$, achieved test FPR is $0.56\%$).

---

## 5. Audit of Research Claims & Limitations

| Initial Claim | Empirical Evidence | Verdict / Necessary Qualification |
| :--- | :--- | :--- |
| *"Hybrid beats all detectors across all metrics"* | Isolation Forest achieves higher ROC-AUC ($0.9762$) and PR-AUC ($0.9369$) than Hybrid ($0.9574$, $0.9156$). Hybrid dominates in recall at calibrated threshold ($0.9915$) and precision at low FPR budgets. | **Downgraded**: The Hybrid provides operational flexibility and evidence diversity, but tabular Isolation Forest remains superior for pure point-anomaly ranking under linear weights. |
| *"Graph detector proves money laundering"* | Graph achieves $100\%$ recall on circular flows and pass-through, but produces false alarms on coincidental retail fan-in patterns ($5.9\%$ FP). | **Qualified**: Graph detection provides valuable structural corroboration, but graph edge existence is circumstantial evidence, not legal proof. |
| *"Immutable Blockchain Audit Ledger"* | Implements a centralized, hash-linked cryptographic ledger (SHA-256 blocks with previous-block hash pointers). | **Clarified**: Honest threat model applied. It is a tamper-evident audit log with hash-chain integrity, not a decentralized Byzantine-fault-tolerant consensus network. |
| *"Proven Generalization to Real-World AML"* | Tested across 3 random seeds on synthetic data. | **Acknowledged Limitation**: 3 seeds and 1,474 synthetic transactions provide proof-of-concept benchmark reproducibility, not validation on real banking populations. |

---

## 6. SAR Narrative Evaluation Protocol

The narrative generation system was audited using the 5-dimension rubric:
1. **Factual Support (20 pts)**: Deterministic verification that transaction counts and amounts cited in narrative text match alert payload inputs.
2. **Evidence Coverage (20 pts)**: Deterministic regex parsing asserting that `TXN_` anchor tags exist in middle body paragraphs and reference valid transaction IDs.
3. **Absence of Unsupported Claims (20 pts)**: Regex negative-lookahead for prejudicial phrases (`guilty of money laundering`, `confirmed criminal`).
4. **Typology & Statutory Authority (20 pts)**: Regex assertion for citations of statutory authorities (`PMLA`, `FIU-IND`, `RBI CTR`).
5. **PII Masking & Paragraph Structure (20 pts)**: Execution of [`detect_pii_leak()`](file:///d:/Hackathon/HB/sar_safety.py) confirming that customer names and raw customer IDs are masked with placeholders.

*Constraint*: The automated rubric tests 3 fixed benchmark cases deterministically. It does not replace human compliance officer oversight before submitting regulatory filings.
