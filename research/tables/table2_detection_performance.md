| Model Architecture | Threshold ($	au$) | TP | FP | TN | FN | Precision | Recall | F1 Score | FPR | Alert Rate | ROC-AUC | PR-AUC |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Rules Engine Only** | 0.50 | 7 | 1 | 176 | 111 | 0.8750 | 0.0593 | 0.1111 | 0.0056 | 0.0271 | 0.5268 | 0.4282 |
| **Isolation Forest (Tabular)** | 0.50 | 113 | 8 | 169 | 5 | 0.9339 | 0.9576 | 0.9456 | 0.0452 | 0.4102 | 0.9762 | 0.9369 |
| **NetworkX Graph Detector** | 0.50 | 62 | 11 | 166 | 56 | 0.8493 | 0.5254 | 0.6492 | 0.0621 | 0.2475 | 0.7322 | 0.6479 |
| **Hybrid Ensemble ($	au=0.20^*$)** | 0.20 | 117 | 18 | 159 | 1 | 0.8667 | 0.9915 | 0.9249 | 0.1017 | 0.4576 | 0.9574 | 0.9156 |
| **Hybrid Ensemble ($	au=0.50$)** | 0.50 | 25 | 1 | 176 | 93 | 0.9615 | 0.2119 | 0.3472 | 0.0056 | 0.0881 | 0.9574 | 0.9156 |

*\*Threshold selected on Validation partition without access to test labels.*
