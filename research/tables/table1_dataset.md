| Partition | Transactions | Suspicious (Positive) | Benign (Negative) | Positive Rate | Time Window Coverage | Purpose |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Training** | 884 | 0 | 884 | 0.00% | 2026-01-01 to 2026-01-24 | Baseline customer profile & Isolation Forest fitting |
| **Validation** | 295 | 42 | 253 | 14.24% | 2026-01-24 to 2026-02-08 | Threshold calibration & FPR budget tuning |
| **Test (Frozen)** | 295 | 118 | 177 | 40.00% | 2026-02-08 to 2026-03-01 | Unbiased benchmark evaluation & matched-FPR comparison |
| **Total Benchmark** | 1,474 | 160* | 1,314 | 10.85% | 2026-01-01 to 2026-03-01 | End-to-end framework validation |
