# Experiment Reproduction Guide and Environment Manifest

**Project Title**: A Hybrid AML Detection and Evidence-Grounded SAR Generation Framework with Tamper-Evident Audit Logging  
**Repository Working Directory**: `d:\Hackathon\HB`  
**Manifest Hash Reference**: [`reports/reproducibility_manifest.json`](file:///d:/Hackathon/HB/reports/reproducibility_manifest.json)  

---

## 1. System & Software Specifications

The entire benchmark and verification pipeline runs on standard commodity hardware. The reference environment was configured as follows:

| Environment Property | Verified Value |
| :--- | :--- |
| **Operating System** | Windows 11 (AMD64) |
| **Python Version** | Python 3.12.0 (CPython 64-bit) |
| **Package Manager** | pip 23.2.1 / 26.2.1 |
| **PyTest Framework** | pytest 9.1.1, pluggy 1.6.0 |
| **Scikit-Learn Version** | 1.9.1 |
| **NetworkX Version** | 3.7 |
| **NumPy Version** | 2.5.3 |
| **Pydantic Version** | 2.13.5 |
| **Sentence-Transformers** | 6.1.0 (`all-MiniLM-L6-v2`) |
| **ChromaDB Version** | 1.5.9 |
| **FastAPI Version** | 0.141.1 |
| **ReportLab Version** | 5.0.1 |
| **Matplotlib Version** | 3.11.2 |

---

## 2. Frozen Data Artifacts & Cryptographic Checksums

The benchmark dataset consists of 1,474 transactions chronologically generated using deterministic random seed `42`. File integrity must be validated against the following SHA-256 digests:

```text
data/synthetic/transactions.csv
SHA-256: dd08901f9fa4573199ca29671607efbf15783309a63327d5bfd96d9da1bcfca6

data/synthetic/scenario_ground_truth.csv
SHA-256: d24e805adfcbc718501e74f88e6a27e90b844ca81014168019e04835694c92b2

data/synthetic/accounts.csv
SHA-256: 76dba1e92822a10df85fb25d2b0cb03fec65674720ae3b0544bf79efc76d2966

data/synthetic/customers.csv
SHA-256: 00e3e1282d8c3066df95886915357876b6ef943e86c0c16922ca95eb04b7754b

data/synthetic/investigation_cases.jsonl
SHA-256: 2674a3c58a52912443fa7cb0bf4a646c2436d4f4ce3d95c4749fbaf93a52f495

rag_pipeline/rules.yaml
SHA-256: 1e22f04cd5aa316a1b1458e0fc6cf72ebc5b8b9ef59f27306eb6ca82c23fa9f9
```

---

## 3. Step-by-Step Reproduction Instructions

### Step 3.1: Environment Activation
Ensure the project virtual environment is active in PowerShell:
```powershell
Set-Location -Path "d:\Hackathon\HB"
& ".\.venv\Scripts\Activate.ps1"
```

### Step 3.2: Automated Regression and Integrity Testing
Execute the complete verification test suite:
```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_robustness_metrics.py tests/test_benchmark_integration.py tests/test_synthetic_generator.py -v
```
*Expected Result*: 10 tests passed (100% pass rate).

### Step 3.3: Re-generating Results Tables (Tables 1 through 5)
Run the automated table extraction script to generate both Markdown (`.md`) and LaTeX (`.tex`) tables in `research/tables/`:
```powershell
.\.venv\Scripts\python.exe scripts/compute_research_tables.py
```
*Outputs Created*:
- `research/tables/table1_dataset.md` and `.tex`
- `research/tables/table2_detection_performance.md` and `.tex`
- `research/tables/table3_typologies.md` and `.tex`
- `research/tables/table4_matched_operating_points.md` and `.tex`
- `research/tables/table5_multi_seed_robustness.md` and `.tex`

### Step 3.4: Re-generating Publication Figures (Figures 1 through 7)
Run the figure generation script to render vector SVG diagrams and 300-DPI publication PNGs in `research/figures/`:
```powershell
.\.venv\Scripts\python.exe scripts/generate_research_figures.py
```
*Outputs Created*:
- `fig1_system_architecture.svg` / `.png`
- `fig2_detection_pipeline.svg` / `.png`
- `fig3_graph_typologies.svg` / `.png`
- `fig4_sar_generation.svg` / `.png`
- `fig5_human_review_audit.svg` / `.png`
- `fig6_evaluation_workflow.svg` / `.png`
- `fig7_detection_visualizations.svg` / `.png`

### Step 3.5: Direct Verification of Authoritative Predictions
Inspect and compute metrics directly from the raw detector score distributions:
```powershell
.\.venv\Scripts\python.exe -c "
import json, numpy as np
from sklearn.metrics import precision_recall_fscore_support, roc_auc_score, average_precision_score, confusion_matrix
with open('reports/frozen_predictions/test_predictions_authoritative.json') as f: data = json.load(f)
y = np.array([1 if p['is_suspicious_ground_truth'] else 0 for p in data])
s_hy = np.array([p['score_hybrid'] for p in data])
pred = (s_hy >= 0.20).astype(int)
tn, fp, fn, tp = confusion_matrix(y, pred).ravel()
print(f'Hybrid (tau=0.20): TP={tp}, FP={fp}, TN={tn}, FN={fn}')
print(f'Precision={tp/(tp+fp):.4f}, Recall={tp/(tp+fn):.4f}, F1={2*tp/(2*tp+fp+fn):.4f}')
"
```
*Expected Output*:
`Hybrid (tau=0.20): TP=117, FP=18, TN=159, FN=1`  
`Precision=0.8667, Recall=0.9915, F1=0.9249`
