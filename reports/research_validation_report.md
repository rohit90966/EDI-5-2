# AML Multi-Detector Framework: Research Validation & Reproducibility Report

**Date of Execution:** 2026-10-17  
**Environment:** Python 3.12 (Windows), scikit-learn 1.9.1, NetworkX 3.7, NumPy 2.5.3, SciPy 1.15.1  
**Repository Working Directory:** `d:\Hackathon\HB`  
**Test Suite Status:** 66 passed in 29.19s (100% test pass rate)  
**Evaluation Scope:** Rules-Only, Isolation Forest-Only, NetworkX Graph-Only, and Multi-Detector Hybrid Decisioning  

---

## 1. Executive Summary

This validation audit independently examines the empirical claims, baseline metrics, graph topology detectors, statistical significance, SAR narrative generation quality, and audit ledger integrity of the hybrid AML detection framework.

### Key Empirical Findings:
1. **Baseline Reproduction:** The exact baseline metrics reported in earlier runs were successfully reproduced at seed 42 ($N = 283$ transactions, 38 positive, 245 benign). Full Hybrid achieves **$\text{F1} = 0.9024$** compared to **$\text{F1} = 0.8837$** for Isolation Forest and **$\text{F1} = 0.7937$** for Rules.
2. **Resolution of PR-AUC Paradox:** The apparent contradiction where Hybrid PR-AUC ($0.7863$) was lower than Isolation Forest PR-AUC ($0.7917$) despite a higher F1-score ($0.9024$ vs $0.8837$) is rigorously explained: F1 is a point metric at an optimal threshold ($0.40$), whereas PR-AUC is a continuous ranking metric. High false positive rates in the graph detector ($152$ false alarms on normal accounts) elevate benign transactions into intermediate score bands, degrading precision across lower thresholds.
3. **Multi-Seed Robustness ($N = 10$ Seeds):** Across 10 stochastic seeds ($42, 101, 202, 303, 404, 505, 606, 707, 808, 909$), the Hybrid Framework significantly outperforms Isolation Forest in Precision ($0.8637$ vs $0.7242$, $+0.1395$, $p < 0.0001$) and F1-Score ($0.9136$ vs $0.8367$, $+0.0769$, $p < 0.0001$), while controlling alert volume ($15.2\%$ vs $18.5\%$).
4. **Typology Complementarity:** Deterministic rules achieve $100\%$ recall on structuring but $0\%$ on circular funds loops. The graph detector achieves $100\%$ recall on circular loops and $90\%$ on fan-in/fan-out mule hubs.
5. **Ledger Tamper Audit:** Mathematical hash-chain verification correctly detects payload modifications, block deletions, and sequence reordering. However, full-chain recomputation proves that a database-only hash chain does not constitute independent tamper resistance against a database administrator without external notary/PKI anchoring.

---

## 2. Baseline Reproduction & Metric Verification

All four core models and two ablation baselines were executed under identical conditions using seed 42 ($283$ transactions, $38$ ground-truth suspicious, $245$ benign background).

### Table 1: Exact Baseline Reproduction Matrix (Seed 42)

| Model Architecture | Confusion Matrix (TP, FP, TN, FN) | Precision | Recall | F1-Score | PR-AUC | ROC-AUC | Alert Rate |
|---|---|---|---|---|---|---|---|
| **Rules Only** | `TP=25, FP=0, TN=245, FN=13` | 1.0000 | 0.6579 | 0.7937 | 0.7038 | 0.8289 | 0.0883 |
| **Isolation Forest Only** | `TP=38, FP=10, TN=235, FN=0` | 0.7917 | 1.0000 | 0.8837 | 0.7917 | 0.9796 | 0.1696 |
| **Graph Network Only** | `TP=15, FP=152, TN=93, FN=23` | 0.0898 | 0.3947 | 0.1463 | 0.1167 | 0.3872 | 0.5901 |
| **Rules + Anomaly (Ablation)** | `TP=25, FP=0, TN=245, FN=13` | 1.0000 | 0.6579 | 0.7937 | 0.9287 | 0.9930 | 0.0883 |
| **Rules + Graph (Ablation)** | `TP=15, FP=152, TN=93, FN=23` | 0.0898 | 0.3947 | 0.1463 | 0.2242 | 0.5215 | 0.5901 |
| **Full Hybrid Framework** | `TP=37, FP=7, TN=238, FN=1` | **0.8409** | **0.9737** | **0.9024** | **0.7863** | **0.9625** | **0.1555** |

### Mathematical Verification of Metrics:
- **Rules Precision:** $\frac{25}{25 + 0} = 1.0000$; **Recall:** $\frac{25}{25 + 13} = 0.6579$; **F1:** $2 \times \frac{1.0 \times 0.6579}{1.0 + 0.6579} = 0.7937$.
- **Isolation Forest Precision:** $\frac{38}{38 + 10} = 0.7917$; **Recall:** $\frac{38}{38 + 0} = 1.0000$; **F1:** $2 \times \frac{0.7917 \times 1.0}{1.7917} = 0.8837$.
- **Hybrid Precision:** $\frac{37}{37 + 7} = 0.8409$; **Recall:** $\frac{37}{37 + 1} = 0.9737$; **F1:** $2 \times \frac{0.8409 \times 0.9737}{0.8409 + 0.9737} = 0.9024$.

---

## 3. Deep-Dive: Resolution of the PR-AUC vs. F1 Paradox

In the baseline evaluation report, the Full Hybrid system achieved a higher point F1-score ($0.9024$ vs $0.8837$) but a slightly lower PR-AUC ($0.7863$ vs $0.7917$) than Isolation Forest alone.

### Root Cause Analysis:
1. **Point Metric vs. Integral Ranking Metric:**
   - **F1-score** is calculated at a single operational decision threshold ($\tau = 0.40$ for Hybrid, $\tau = 0.50$ for Anomaly). At $\tau = 0.40$, the Hybrid aggregation suppresses $3$ false positives from the anomaly detector (reducing FP from $10$ to $7$) while retaining $37$ of $38$ true positives. This boosts precision from $79.2\%$ to $84.1\%$ and yields the highest F1.
   - **PR-AUC (Average Precision)** integrates precision across *all* possible score thresholds ($\tau \in [0, 1]$).
2. **Score Discretization in the Benchmark Harness:**
   - In `evaluation/evaluator.py`, detector findings were mapped to discrete scores ($s_a \in \{0.85, 0.05\}$, $s_g \in \{0.90, 0.02\}$, $s_r \in \{0.85, 0.04\}$).
   - For Isolation Forest alone, the score distribution is a binary step function. PR-AUC for a binary step equals:
     $$\text{PR-AUC}_{\text{IF}} = (\text{Recall}_1 - \text{Recall}_0) \times \text{Precision}_1 = 1.0 \times \frac{38}{38 + 10} = 0.7917$$
   - In the Hybrid system, scores are formed by linear combination: $S_{\text{hybrid}} = 0.35 r + 0.25 a + 0.40 g$.
   - Because the Graph detector flags $152$ normal transactions as rapid pass-throughs ($g = 0.90$), these benign transactions receive a score component of $0.40 \times 0.90 = 0.360$.
   - Consequently, benign transactions with $r = 0.04, a = 0.05, g = 0.90$ attain $S_{\text{hybrid}} = 0.3865$.
   - Meanwhile, true positive accounts that only triggered anomaly detection ($r = 0.04, a = 0.85, g = 0.02$) attain $S_{\text{hybrid}} = 0.2345$.
   - When sorting transactions by score to compute the Precision-Recall curve, the graph false positives ($S = 0.3865$) are ranked *ahead* of these true positive transactions ($S = 0.2345$). When threshold sweeps down through $0.38$, precision drops sharply before recovering, lowering the total area under the PR curve.
3. **Resolution:** Over the multi-seed evaluation ($N = 10$ seeds, Table 2), the continuous mean PR-AUC of Hybrid is **$0.8038 \pm 0.0442$**, which is higher than Isolation Forest's mean PR-AUC of **$0.7199 \pm 0.0486$** ($p = 0.00192$). The seed 42 artifact was an edge effect of discrete score steps interacting with graph false positives.

---

## 4. Evaluation Hygiene & Data Leakage Audit

A thorough audit of `ml/features.py`, `evaluation/synthetic_generator.py`, and `evaluation/evaluator.py` revealed four critical methodological observations:

1. **Temporal Leakage Prevention (VERIFIED):**
   - Feature extraction in `ml/features.py` strictly restricts historical baseline calculations (median, MAD, and rolling velocity windows) to transactions with `timestamp < target_ts`.
   - The target transaction is completely excluded from its own baseline, preventing variance self-contamination.
2. **Label Leakage Check (VERIFIED):**
   - `perform_leakage_check()` confirms that ground-truth labels (`is_suspicious`, `typology`) are absent from transaction records and extracted feature matrices.
3. **Synthetic Shortcut Disclosure:**
   - In `evaluation/evaluator.py` lines 150-154, rule evaluation on synthetic streams used a heuristic shortcut:
     `is_rule_flag = (txn.get("country") == "UAE" or (45000 <= txn.get("amount", 0) <= 50000))`
   - *Audit Assessment:* In the real pipeline, `RulesEngineDetector` evaluates aggregated account alerts rather than individual transaction records. While this shortcut accurately mirrors the ground truth structuring and UAE cross-border rules, an academic publication should explicitly document that transaction-level rule scores represent account-level rule attribution mapped to constituent transactions.
4. **Threshold Selection Disclosure:**
   - In `evaluation/evaluator.py`, individual detectors were evaluated at $\tau = 0.50$, two-way ablations at $\tau = 0.45$, and the Hybrid detector at $\tau = 0.40$.
   - *Audit Assessment:* These thresholds were post-hoc selected rather than cross-validated via a dedicated validation split. In production, thresholds should be calibrated against an ROC/PR validation curve.

---

## 5. Multi-Seed Robustness & Statistical Significance Analysis

To assess whether the Hybrid framework's performance gains over Isolation Forest are statistically significant or merely an artifact of seed 42, a multi-seed experiment was conducted across **10 pseudo-random seeds** ($42, 101, 202, 303, 404, 505, 606, 707, 808, 909$).

### Table 2: Multi-Seed Aggregate Performance Metrics ($N = 10$ Seeds)

| Model Architecture | Precision (Mean $\pm$ SD) | 95% Confidence Interval | Recall (Mean $\pm$ SD) | 95% Confidence Interval | F1-Score (Mean $\pm$ SD) | 95% Confidence Interval | PR-AUC (Mean $\pm$ SD) |
|---|---|---|---|---|---|---|---|
| **Rules Only** | $1.0000 \pm 0.0000$ | $[1.0000, 1.0000]$ | $0.6316 \pm 0.0277$ | $[0.6118, 0.6514]$ | $0.7739 \pm 0.0207$ | $[0.7591, 0.7887]$ | $0.6813 \pm 0.0232$ |
| **Isolation Forest Only** | $0.7242 \pm 0.0432$ | $[0.6933, 0.7551]$ | $\mathbf{0.9921 \pm 0.0178}$ | $[0.9794, 1.0048]$ | $0.8367 \pm 0.0325$ | $[0.8135, 0.8600]$ | $0.7199 \pm 0.0486$ |
| **Graph Network Only** | $0.1161 \pm 0.0167$ | $[0.1042, 0.1281]$ | $0.3973 \pm 0.0083$ | $[0.3914, 0.4033]$ | $0.1791 \pm 0.0204$ | $[0.1646, 0.1937]$ | $0.1274 \pm 0.0078$ |
| **Full Hybrid Framework** | $\mathbf{0.8637 \pm 0.0372}$ | $[0.8370, 0.8903]$ | $0.9711 \pm 0.0230$ | $[0.9546, 0.9875]$ | $\mathbf{0.9136 \pm 0.0209}$ | $[0.8987, 0.9286]$ | $\mathbf{0.8038 \pm 0.0442}$ |

### Table 3: Average Confusion Matrices ($N = 10$ Seeds)

| Architecture | Average TP | Average FP | Average TN | Average FN | Average Alert Rate |
|---|---|---|---|---|---|
| **Rules Only** | 24.0 | 0.0 | 244.2 | 14.0 | 8.5% |
| **Isolation Forest Only** | 37.7 | 14.5 | 229.7 | 0.3 | 18.5% |
| **Graph Network Only** | 15.1 | 117.4 | 126.8 | 22.9 | 47.0% |
| **Full Hybrid Framework** | 36.9 | **5.9** | 238.3 | 1.1 | **15.2%** |

### Table 4: Paired Statistical Comparison: Hybrid vs. Isolation Forest ($N = 10$)

| Evaluated Metric | Mean Difference ($\Delta$) | Paired $t$-Statistic | Student's $p$-Value | Wilcoxon Signed-Rank $p$ | Significant at $\alpha = 0.05$? |
|---|---|---|---|---|---|
| **F1-Score** | **$+0.0769$** | $t = 7.3985$ | $p = 0.00004$ | $p = 0.00195$ | **YES (Highly Significant)** |
| **Precision** | **$+0.1395$** | $t = 7.8842$ | $p = 0.00002$ | $p = 0.00195$ | **YES (Highly Significant)** |
| **Recall** | $-0.0210$ | $t = -6.0000$ | $p = 0.00020$ | $p = 0.00781$ | **YES (IF has slightly higher raw recall)** |
| **PR-AUC** | **$+0.0839$** | $t = 4.3245$ | $p = 0.00192$ | $p = 0.00586$ | **YES (Highly Significant)** |
| **ROC-AUC** | $+0.0031$ | $t = 0.8524$ | $p = 0.41608$ | $p = 0.44531$ | NO (Roughly equivalent ranking power) |

### Sample Scale Limitations:
* **Dataset Size:** The synthetic benchmark generates $\sim 283$ transactions across $20$ normal accounts and $4$ synthetic typologies per run. While 10 distinct seeds validate variance and algorithmic stability, the total sample of positive cases per seed is modest ($38$ positive instances).
* **Statistical Caution:** While the paired $t$-test indicates $p < 0.001$, student research publications should explicitly state that synthetic datasets with stylized topologies tend to overestimate separability relative to real-world noisy banking data.

---

## 6. Typology-Specific Error Analysis

A breakdown of detector recalls across each suspicious money laundering typology and benign control group illuminates the specific strengths and failure modes of each detector.

### Table 5: Typology Recall & Error Analysis ($N = 10$ Seeds)

| Evaluated Typology | Positive Count | Rules Recall | Anomaly Recall | Graph Recall | Hybrid Recall | Primary Detection Mechanism / Failure Mode |
|---|---|---|---|---|---|---|
| **STRUCTURING** | 22 | $100.0\%$ | $100.0\%$ | $0.0\%$ | **$100.0\%$** | Multiple deposits just below threshold. Captured by Rules & IF; Graph has 0% recall (parallel transfers to single account are not a cycle). |
| **PASS_THROUGH** | 2 | $50.0\%$ | $100.0\%$ | $100.0\%$ | **$100.0\%$** | Inbound credit drained to UAE. Graph catches temporal proximity; Rules catch cross-border destination. |
| **CIRCULAR_FLOW** | 4 | $0.0\%$ | $100.0\%$ | $100.0\%$ | **$100.0\%$** | $A \to B \to C \to D \to A$. **Rules fail completely ($0\%$)**; Graph simple cycles catch $100\%$. |
| **FAN_IN_FAN_OUT** | 10 | $20.0\%$ | $100.0\%$ | $90.0\%$ | **$90.0\%$** | Mule collection hub. High in/out degree detected by Graph; Anomaly flags velocity outliers. |
| **BENIGN_BONUS** | 1 | $0.0\%$ | $100.0\%$ | $0.0\%$ | **$0.0\%$** | Benign one-off bonus. **IF produces False Positive**; Hybrid correctly suppresses it. |
| **BENIGN_INVEST** | 1 | $0.0\%$ | $100.0\%$ | $0.0\%$ | **$0.0\%$** | Large mutual fund investment. **IF produces False Positive**; Hybrid correctly suppresses it. |
| **BENIGN_MERCHANT**| 12 | $0.0\%$ | $0.0\%$ | $0.0\%$ | **$0.0\%$** | Rapid retail e-commerce settlements. Correctly classified as benign by Hybrid. |

### Graph Detector Error Analysis:
* **The Rapid Pass-Through False Positive Spike (117-152 FPs):**
  - *Observation:* The Graph detector alone exhibited an alarm rate of $47.0\% - 59.0\%$, generating $117.4$ average false positives on benign background transactions.
  - *Mechanism:* In `graph/graph_detector.py`, the pass-through condition flags any node where inbound credit is followed by outbound debit within $72$ hours and $\frac{\text{Debit}}{\text{Credit}} \ge 0.75$.
  - *Root Cause:* In normal personal banking, ordinary consumers receive monthly salary and pay rent/groceries within 72 hours. Without an absolute minimum amount threshold (e.g. $\ge 100,000$ INR) or commercial counterparty exemption, normal living expenses match the rapid pass-through motif.
  - *Smallest Justified Recommendation:* Introduce a parameter `min_pass_through_amount: float = 100000.0` in `GraphLaunderingDetector`. Because the project mission requires freezing production parameters on the test set, this adjustment is documented as a research recommendation rather than retrofitted post-hoc.

---

## 7. Hybrid Aggregation, Weights, and Policy Verification

The multi-detector aggregation and decisioning layer was audited against the source code in `detection/aggregator.py` and `detection/policy.py`.

### Table 6: Implementation Configuration Verification

| Subsystem Component | Prespecified / Configured Value | Verification Evidence | Design Rationale |
|---|---|---|---|
| **Rules Engine Weight** | $0.35$ | `detection/aggregator.py#L14` | Prespecified domain heuristic. Direct regulatory rule breaches carry strong compliance weight. |
| **Isolation Forest Weight** | $0.25$ | `detection/aggregator.py#L15` | Prespecified domain heuristic. Unsupervised behavioral anomalies provide broad coverage but require corroboration. |
| **Graph Detector Weight** | $0.40$ | `detection/aggregator.py#L16` | Prespecified domain heuristic. Structural laundering networks (cycles, hubs) represent organized typologies. |
| **SAR Draft Threshold** | $\tau \ge 0.50$ | `detection/policy.py#L18` | Prespecified threshold. Score $\ge 0.50$ or $\ge 2$ rules triggers SAR drafting eligibility. |
| **Analyst Review Baseline**| $\tau \ge 0.25$ | `detection/policy.py#L19` | Prespecified monitoring baseline. Score $\ge 0.25$ or any finding requires manual analyst review. |
| **Degraded Detector Safety**| Mandatory Analyst Review | `detection/policy.py#L83` | **Verified Fix:** Any analysis with status `PARTIAL` enforces `requires_analyst_review = True`. |

---

## 8. SAR Narrative Quality Evaluation (Documented 5-Dimension Rubric)

SAR narrative generation was evaluated across three distinct fixed benchmark cases (`CASE_01_STRUCTURING_RETAIL`, `CASE_02_RAPID_PASSTHROUGH_UAE`, and `CASE_03_CIRCULAR_FLOW_LOOP`) using an objective 100-point rubric.

### Table 7: SAR Narrative Quality Evaluation Rubric (Dual Evaluation)

| Rubric Dimension | Max Points | Evaluation Criteria | Benchmark Baseline (Offline) | Live Ollama (`qwen2.5:7b`) Empirical | Failure Mode / Deduction Notes in Live Model |
|---|---|---|---|---|---|
| **1. Factual Support** | 20 pts | Transaction counts, amounts, and timeframes match case data without hallucinated values. | 20.0 / 20 | 15.0 / 20 | -5.0: Model rounded or paraphrased aggregate amounts from few-shot context. |
| **2. Evidence Coverage** | 20 pts | Sentences are anchored to valid transaction IDs (`[TXN_...]` / `(TXN_...)`). | 20.0 / 20 | 10.0 / 20 | -10.0: **Prompt few-shot contamination**: Model copied example IDs (`TXN_00031`, `TXN_00032`) instead of case IDs (`TXN_STR_001`). |
| **3. Absence of Hallucinations** | 20 pts | Free of unsupported legal accusations or invented criminal cartels. | 20.0 / 20 | **20.0 / 20** | **0.0:** Zero prejudicial or defamatory legal accusations. |
| **4. Typology & Citation** | 20 pts | Cites specific AML typologies and statutory authorities (PMLA, RBI, FIU-IND). | 20.0 / 20 | **20.0 / 20** | **0.0:** Accurately cited PMLA Section 12 and applicable typologies. |
| **5. PII Suppression & Structure** | 20 pts | Zero exposure of customer names or IDs. Strict 5-paragraph structure. | 20.0 / 20 | 15.0 / 20 | **0.0 PII leaks**; -5.0: Model wrapped output in markdown ````json ```` code block rather than raw text. |
| **Total Score / Grade** | **100 pts** | $\ge 90$: EXCELLENT, $\ge 75$: ACCEPTABLE, $< 75$: REJECTED | **100.0 (EXCELLENT)** | **80.0 (ACCEPTABLE)** | **Zero PII exposure; acceptable compliance drafting.** |

### Empirical Analysis of Live Local LLM (`qwen2.5:7b`) Execution:
1. **PII Safety Invariance (100% Maintained):** Across all three live generated cases, customer names (`Rajesh Kumar`, `Vikram Sethi`, `Deepak Verma`) and customer IDs were completely suppressed by the post-processing filter.
2. **The Few-Shot Prompt Contamination Flaw:** In live evaluation, the 7B model suffered from few-shot bias: it copied transaction ID placeholders (`TXN_00031`, `TXN_00032`) directly from the few-shot template in `rag_pipeline/pipeline_service.py` rather than extracting the real transaction IDs supplied in the user prompt.
   * *Recommended Prompt Optimization:* Replace fixed transaction IDs in few-shot prompt examples with abstracted placeholders (`TXN_EXAMPLE_A`, `TXN_EXAMPLE_B`) and add a negative constraint: *"NEVER use example transaction IDs in the final report."*
3. **Inference Provider Quota Limitation:** The remote Hugging Face Inference API returned HTTP `402 Payment Required` (`HF_API_TOKEN` exhausted). The project successfully fell back to the local Ollama instance (`qwen2.5:7b`), demonstrating operational resilience without system stoppage.

---

## 9. Audit Ledger Tamper Verification & Threat Model

The cryptographic append-only audit ledger (`audit/ledger.py`) was subjected to four deliberate attack vectors in `tests/test_audit_verification.py`.

### Table 8: Audit Ledger Tamper Verification Results

| Attack Vector | Simulated Action | Expected Behavior | Verification Status | Failure Category |
|---|---|---|---|---|
| **1. Payload Tampering** | Altered transaction amount in Block 2 payload (`1000` $\to$ `999999999`). | Recalculated payload hash does not match stored block header. | **DETECTED** | `PAYLOAD_TAMPER` |
| **2. Block Deletion** | Deleted Block 2 from 3-block chain ($[1, 2, 3] \to [1, 3]$). | Discontinuity in sequence numbers ($1 \to 3$) and broken link ($H_3.\text{prev} \ne H_1$). | **DETECTED** | `SEQUENCE_GAP` |
| **3. Block Reordering** | Swapped sequence numbers between Block 2 and Block 3. | Sequence inversion and broken hash chain pointer. | **DETECTED** | `LINK_TAMPER` / `HASH_TAMPER` |
| **4. Full-Chain Rewriting** | Attacker rewrites Block 2 and recomputes all subsequent block hashes. | Internal mathematical chain recomputes cleanly; `verify_ledger()` passes. | **CONFIRMED THREAT** | Internal Check Passes |

### Honest Threat Model & Independent Tamper Resistance Distinction:
* **Hash-Chain Integrity vs. Immutable Notarization:**
  - A database-resident SHA-256 hash chain guarantees *detectability of unauthorized modifications* only if the verification utility has an independent, trusted anchor (such as a genesis root or external checkpoint).
  - An attacker with administrative privileges (`postgres` superuser access) who modifies a record and recomputes all downstream hashes using the open-source hashing function can present an internally valid hash chain.
  - **Academic Conclusion:** Do not claim that a local PostgreSQL hash chain constitutes a decentralized blockchain or immutable decentralized ledger. To achieve independent tamper resistance against database administrators, the system must periodically anchor block root hashes to an external timestamping authority (RFC 3161) or a public decentralized blockchain.

---

## 10. Reproducibility Guide & Commands

All experiments, benchmarks, and tests can be reproduced using the following commands in the virtual environment:

```powershell
# 1. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 2. Run the complete test suite (66 tests)
pytest -v

# 3. Reproduce single-seed baseline evaluation (Seed 42)
python scripts\run_evaluation.py --seed 42

# 4. Reproduce multi-seed statistical evaluation (N=10 seeds with paired tests)
python scripts\multi_seed_evaluation.py

# 5. Reproduce SAR narrative quality rubric evaluation
python evaluation\sar_narrative_eval.py

# 6. Verify cryptographic audit ledger integrity
python scripts\verify_audit_ledger.py
```

---

## 11. Prioritized List of Remaining Issues & Recommendations

| Priority | Component | Issue Description | Recommended Action for Future Work |
|---|---|---|---|
| **P1** | Graph Detector | Rapid pass-through flags ordinary personal banking expenses ($117$ avg FPs). | Add `min_pass_through_amount = 100000.0` and merchant counterparty category filter. |
| **P2** | LLM Provider | Remote Hugging Face token exhausted (402 error). | Configure an active API key or lightweight quantized local model (`phi3:mini` or `gemma:2b`). |
| **P3** | Evaluation Harness | Transaction-level rules evaluate via synthetic heuristic rather than account aggregation. | Implement a transaction-to-account adapter in the benchmark harness to run `RulesEngineDetector` natively. |
| **P4** | Audit Ledger | Database hash chain vulnerable to full-chain rewriting by superusers. | Implement external Merkle root checkpointing (RFC 3161 or public testnet anchor). |
| **P5** | Model Training | Isolation Forest trained dynamically on batch rather than pre-trained on reference cohort. | Pre-train on a reference benign cohort and serialize via joblib artifact for zero inference training overhead. |

---
*Report prepared and validated against the actual repository codebase.*
