# Model Card: Behavioral Anomaly Detection (Isolation Forest)

**Model Identifier:** `isoforest-v1.0`  
**Model Type:** Unsupervised Ensemble Tree Outlier Estimator (`sklearn.ensemble.IsolationForest`)  
**Developer:** Applied ML Research & AML Systems Team  
**Release Date:** October 2026  

---

## 1. Intended Use & Scope

- **Primary Application:** Flags statistical outliers in account transaction behavior (unusual amounts, abnormal velocities, new-counterparty surges) to guide compliance analyst prioritization.
- **Out of Scope & Prohibited Use:**
  - This model must **never** be used as standalone proof of criminality or money laundering.
  - Anomaly scores are **not** calibrated fraud probabilities; an anomaly indicates statistical deviation, which frequently has benign explanations (e.g., seasonal spending, bonus payouts, house purchases).
  - The model does not make adverse customer decisions or file regulatory reports automatically.

---

## 2. Feature Schema & Engineering

The model operates on a 16-dimensional deterministic feature vector (`FEATURE_SCHEMA_VERSION = "2026.1"`):

| Feature Name | Description | Rationale |
|---|---|---|
| `amount` | Transaction monetary value in INR | Captures absolute magnitude of transfer. |
| `amount_to_median_ratio` | $\text{amount} / \text{median}(\text{preceding})$ | Normalized scale relative to individual account history. |
| `amount_mad_zscore` | $(\text{amount} - \text{median}) / (1.4826 \times \text{MAD})$ | Robust Z-score resistant to historical outlier skew. |
| `rolling_count_24h` | Transaction count in preceding 24 hours | Short-term transaction frequency. |
| `rolling_amount_24h` | Total volume in preceding 24 hours | Rapid burst volume identification. |
| `rolling_count_7d` | Transaction count in preceding 7 days | Medium-term velocity. |
| `rolling_amount_7d` | Total volume in preceding 7 days | Medium-term volume accumulation. |
| `rolling_count_30d` | Transaction count in preceding 30 days | Monthly baseline activity. |
| `rolling_amount_30d` | Total volume in preceding 30 days | Monthly turnover. |
| `unique_counterparties_30d` | Distinct counterparties over 30 days | Breadth of financial network. |
| `new_counterparties_ratio_30d` | Fraction of counterparties never seen prior to 30d | Sudden burst of unfamiliar entities. |
| `velocity_txns_per_day` | Average daily transaction count over 7 days | Standard velocity metric. |
| `hour_sin`, `hour_cos` | $\sin(2\pi h / 24)$, $\cos(2\pi h / 24)$ | Cyclic encoding of transfer time of day. |
| `day_of_week` | Day index (0 = Monday, 6 = Sunday) | Weekend vs. business day patterns. |
| `inflow_outflow_ratio` | $\text{Credits}_{30d} / \text{Debits}_{30d}$ | Balance accumulation vs. pass-through dissipation. |

### Temporal Integrity & Leakage Prevention
All features are extracted strictly from transactions timestamped $\le \text{as\_of\_time}$. Future transactions, target labels, and post-investigation findings are strictly inaccessible during feature building.

---

## 3. Training & Hyperparameters

- **Algorithm:** Isolation Forest partitioning via random feature selection and split points.
- **Tree Count (`n_estimators`):** `100`
- **Contamination Assumption (`contamination`):** `0.05` (specifies the decision boundary cutoff; this is an operational sensitivity tuning parameter, not the empirical fraud rate).
- **Random Seed (`random_state`):** `42` (ensures reproducible tree construction across test runs).
- **Fitting Policy:** Fitted on clean historical partitions or pre-alert baseline windows. The model is **not** retrained dynamically per request in production to avoid drift.

---

## 4. Score Normalization & Interpretation

Raw Isolation Forest `decision_function` values $s \in [-0.5, 0.5]$ (where negative values represent anomalous outliers) are mapped to an uncalibrated index $S \in [0.0, 1.0]$ using a sigmoid transformation:

$$S = \frac{1}{1 + e^{6 \times s}}$$

- **Interpretation:** $S \ge 0.70$ indicates a candidate behavioral anomaly.
- **Classification:** An anomaly score is treated as **Signal Layer B** and combined with Rule findings and Graph findings by the `HybridRiskAggregator`.

---

## 5. Known Limitations & Caveats

1. **Cold Start / Sparse Histories:** Accounts with fewer than 5 transactions cannot reliably establish a statistical distribution. The detector emits an explicit `PARTIAL` status with a caveat warning.
2. **Benign Outliers:** Legitimate life events (e.g., real estate transactions, medical emergencies, annual corporate bonuses) will trigger high anomaly scores. Human analyst review is essential.
3. **Class Imbalance:** In banking environments where true laundering prevalence is $< 0.1\%$, anomaly detection alone produces a high false positive rate unless constrained by deterministic rule corroboration.
