# Synthetic AML Dataset Generator & Evaluation Benchmark

This module provides a reproducible, leakage-safe synthetic data generator and multi-detector evaluation benchmark tailored for banking compliance, AML pattern discovery, and SAR decisioning systems.

---

## 1. Architecture & Design Principles

The generator constructs realistic customer banking lifecycles and structured money-laundering typologies while enforcing strict separation between **detection runtime inputs** and **evaluation ground truth**:

1. **Strict Referential Integrity**: Customers $\to$ Accounts $\to$ Transactions $\to$ Scenarios $\to$ Investigation Cases.
2. **Monotonic Running Balances**: Running balances are continuously reconciled after sorting all transactions chronologically.
3. **Zero Ground-Truth Leakage**:
   - `transactions.csv` never contains labels, flags (`is_suspicious`, `isFlaggedFraud`), or scenario identifiers.
   - Ground truth is stored in an independent `scenario_ground_truth.csv` file.
   - Historical feature calculation in `ml/features.py` strictly considers transactions occurring *prior* to each target transaction timestamp ($t_{prior} < t_{target}$).
4. **Hard Negative Controls**:
   - Legitimate annual corporate bonuses deployed into mutual funds.
   - High-velocity retail merchant UPI POS settlements.
   - Emergency medical hospital payments with rapid consecutive debits.

---

## 2. Generated File Schemas

All datasets are exported into `data/synthetic/`:

| File | Format | Key Fields | Description |
| :--- | :--- | :--- | :--- |
| `transactions.csv` | CSV | `txn_id`, `account_id`, `counterparty`, `amount`, `txn_type`, `country`, `timestamp`, `balance_after`, `purpose_code` | Transaction log free of target labels. |
| `accounts.csv` | CSV | `account_id`, `customer_id`, `account_type`, `opened_date`, `initial_balance`, `current_balance` | Account metadata and balance tracking. |
| `customers.csv` | CSV | `customer_id`, `name`, `occupation`, `monthly_income`, `risk_rating` | Synthetic customer demographics and occupations. |
| `scenario_ground_truth.csv` | CSV | `txn_id`, `account_id`, `scenario_id`, `scenario_family`, `typology`, `is_suspicious_by_construction`, `is_contextual_only`, `confidence` | Ground-truth labels for academic evaluation. |
| `investigation_cases.jsonl` | JSONL | `case_id`, `scenario_id`, `account_id`, `alert_type`, `alert_timestamp`, `window_start`, `window_end`, `ground_truth_typology`, `is_suspicious`, `transaction_ids` | Packaged investigation cases for compliance review. |
| `generation_manifest.json` | JSON | `version`, `generation_timestamp`, `config`, `dataset_statistics`, `leakage_safety_declaration`, `disclaimer` | Generation parameters, random seeds, and reproducibility proof. |

---

## 3. Supported Typologies

### Suspicious-by-Construction Scenarios:
- **Structuring / Smurfing**: Repeated cash/wire deposits just below regulatory reporting thresholds.
- **Rapid Pass-Through**: Inward credits from unverified sources drained within 4–10 hours to high-risk offshore jurisdictions (UAE, Cayman).
- **Circular Flows / Round-Tripping**: Layered loops ($A \to B \to C \to D \to A$) passing funds through multiple accounts with fractional haircuts.
- **Fan-In / Fan-Out (Mule Collection Hub)**: Aggregation from multiple feeder sources followed by rapid dispersal to downstream money mules.
- **Transaction Velocity Bursts**: Abrupt transaction spikes drastically exceeding the customer's historical frequency baseline.

### Benign / Hard-Negative Scenarios:
- **Annual Bonus Investment**: High single-credit salary bonus followed by mutual fund deployment (distinguishing legitimate wealth spikes from illicit structuring).
- **Retail Merchant Peak**: Rapid inward settlements for festival/flash sales (distinguishing high velocity from smurfing).
- **Medical Emergency**: Concentrated hospital bill debits (distinguishing rapid fund depletion from pass-through layering).

---

## 4. Evaluation Benchmark Methodology

1. **Chronological Partitioning**:
   - **Train set** ($60\%$): Used strictly for learning unsupervised baselines (fitting the Isolation Forest).
   - **Validation set** ($20\%$): Used to calibrate decision thresholds (freezing the hybrid cutoff).
   - **Test set** ($20\%$): Unseen future transactions evaluated using frozen models and calibrated thresholds.
2. **Continuous Anomaly Scoring**:
   - Preserves continuous sigmoid anomaly scores ($0.0 \le s \le 1.0$) for smooth PR-AUC and ROC-AUC curve integration.
3. **Comparative Models**:
   - `rules_only`: Rule engine threshold checks.
   - `anomaly_only`: Isolation Forest continuous outlier scoring.
   - `graph_only`: NetworkX directed multigraph pattern detection.
   - `hybrid`: Risk-weighted aggregation combining rules, anomaly, and graph scores.

---

## 5. Reproduction Commands

To generate the dataset and execute the benchmark:
```powershell
python scripts/generate_and_benchmark.py
```

To run the automated verification test suite:
```powershell
python -c "
import tests.test_synthetic_generator as t
from pathlib import Path
tmp = Path('data/tmp_test'); tmp.mkdir(parents=True, exist_ok=True)
t.test_generator_schema_and_referential_integrity(tmp)
t.test_seed_reproducibility(tmp)
t.test_temporal_monotonicity_and_balance_arithmetic()
t.test_zero_leakage_in_features_and_transactions()
t.test_detection_adapter_compatibility()
print('All tests passed!')
"
```

---

## 6. Research Limitations & Academic Disclaimer

- **Fictional Simulation**: All names, companies, bank accounts, and transactions are purely synthetic simulations created for academic AML research.
- **Synthetic vs Real Wrongdoing**: Synthetic ground-truth labels denote transactions that match parameterized AML typology heuristics by construction. They do not constitute proof of real-world criminal liability.
- **Safety**: Generated records are completely decoupled from production payment gateways and banking APIs; they never initiate live financial transactions or file real SARs.
