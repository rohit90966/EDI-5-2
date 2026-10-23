# Comprehensive Research Paper Generation and Artifact Delivery Report

**Project Title**: A Hybrid AML Detection and Evidence-Grounded SAR Generation Framework with Tamper-Evident Audit Logging  
**Date of Completion**: 2026-10-18  
**Lead Research Engineers**: Antigravity Research Pair Programming Agent & Senior AML Domain Researcher  
**Target Venue Tier**: Student / Early-Stage Research Publication (IEEE / ACM / Workshop on AI in Finance)  

---

## 1. Executive Summary and Deliverables Inventory

A complete, technically verified, publication-ready research paper package covering the entire end-to-end AML framework has been generated. The manuscript reflects the actual source code, frozen benchmark predictions, and cryptographic audit mechanics of the repository without exaggerated claims of novelty, uncalibrated probability assertions, or fabricated citations.

All required deliverables have been compiled and saved in the `research/` directory:

| Deliverable Artifact | Description / Format | File Path |
| :--- | :--- | :--- |
| **Complete Research Paper (Markdown)** | Full publication manuscript containing all 15 sections, equations, references, and appendices. | [`research/full_project_research_paper.md`](file:///d:/Hackathon/HB/research/full_project_research_paper.md) |
| **Complete Research Paper (LaTeX)** | Two-column IEEEtran publication-ready LaTeX source file. | [`research/full_project_research_paper.tex`](file:///d:/Hackathon/HB/research/full_project_research_paper.tex) |
| **BibTeX Bibliography** | 18 verified academic and statutory citations. | [`research/references.bib`](file:///d:/Hackathon/HB/research/references.bib) |
| **Paper Audit & Reconciliation** | Detailed audit tracing conflicting claims, source code locations, and authoritative values. | [`research/paper_audit.md`](file:///d:/Hackathon/HB/research/paper_audit.md) |
| **Bibliographic Audit** | Verification report confirming real authors, venues, DOIs, and statutory baselines. | [`research/reference_audit.md`](file:///d:/Hackathon/HB/research/reference_audit.md) |
| **Reproducibility Guide** | Step-by-step commands, dependency environment, seeds, and SHA-256 manifest. | [`research/reproducibility.md`](file:///d:/Hackathon/HB/research/reproducibility.md) |
| **Publication Figures (1–7)** | Vector SVG and 300-DPI publication PNG diagrams and empirical result visualizations. | [`research/figures/`](file:///d:/Hackathon/HB/research/figures/) |
| **Result Tables (1–5)** | Formatted Markdown and LaTeX tables generated directly from authoritative data. | [`research/tables/`](file:///d:/Hackathon/HB/research/tables/) |

---

## 2. Inventory of Figures and Tables

### Figures (in `research/figures/`):
1. **Figure 1**: End-to-end system architecture showing Data Ingestion, Multi-Detector Layer, RAG SAR Generator, Human Review Workbench, and Hash-Chain Ledger ([SVG](file:///d:/Hackathon/HB/research/figures/fig1_system_architecture.svg) / [PNG](file:///d:/Hackathon/HB/research/figures/fig1_system_architecture.png)).
2. **Figure 2**: Multi-detector risk scoring pipeline, score normalization, linear weighting ($0.35, 0.35, 0.30$), degraded-mode handling, and validation thresholding ([SVG](file:///d:/Hackathon/HB/research/figures/fig2_detection_pipeline.svg) / [PNG](file:///d:/Hackathon/HB/research/figures/fig2_detection_pipeline.png)).
3. **Figure 3**: Conceptual transaction graph typologies: Normal baseline, Rapid pass-through, Bounded circular flow loop, Fan-in aggregation hub, and Fan-out dispersal ([SVG](file:///d:/Hackathon/HB/research/figures/fig3_graph_typologies.svg) / [PNG](file:///d:/Hackathon/HB/research/figures/fig3_graph_typologies.png)).
4. **Figure 4**: Evidence-grounded RAG SAR generation pipeline with ChromaDB vector store, local Ollama LLM, PII masking, and 5 structured sections ([SVG](file:///d:/Hackathon/HB/research/figures/fig4_sar_generation.svg) / [PNG](file:///d:/Hackathon/HB/research/figures/fig4_sar_generation.png)).
5. **Figure 5**: Human review lifecycle, RBAC authorization, ReportLab PDF generation, and append-only SHA-256 hash-chained audit ledger ([SVG](file:///d:/Hackathon/HB/research/figures/fig5_human_review_audit.svg) / [PNG](file:///d:/Hackathon/HB/research/figures/fig5_human_review_audit.png)).
6. **Figure 6**: Experimental evaluation workflow: chronological 60/20/20 partitioning, training-only baseline fitting, validation threshold calibration, and frozen test set evaluation ([SVG](file:///d:/Hackathon/HB/research/figures/fig6_evaluation_workflow.svg) / [PNG](file:///d:/Hackathon/HB/research/figures/fig6_evaluation_workflow.png)).
7. **Figure 7**: Empirical performance visualizations: (a) Precision-Recall curves, (b) ROC curves, (c) Typology recall breakdown, (d) Confusion matrix for Isolation Forest ($\tau=0.50$), (e) Confusion matrix for Hybrid ($\tau=0.20$), and (f) Test precision across matched validation FPR budgets ([SVG](file:///d:/Hackathon/HB/research/figures/fig7_detection_visualizations.svg) / [PNG](file:///d:/Hackathon/HB/research/figures/fig7_detection_visualizations.png)).

### Tables (in `research/tables/`):
1. **Table 1**: Dataset composition and chronological partitioning ($N=1{,}474$, 39 accounts, 30 customers, 28 scenarios) ([MD](file:///d:/Hackathon/HB/research/tables/table1_dataset.md) / [TeX](file:///d:/Hackathon/HB/research/tables/table1_dataset.tex)).
2. **Table 2**: Authoritative test-partition detection performance across Rules, Isolation Forest, Graph, and Hybrid architectures ($N=295$, 118 positive, 177 negative) ([MD](file:///d:/Hackathon/HB/research/tables/table2_detection_performance.md) / [TeX](file:///d:/Hackathon/HB/research/tables/table2_detection_performance.tex)).
3. **Table 3**: Per-typology recall breakdown across individual detectors and the hybrid ensemble ([MD](file:///d:/Hackathon/HB/research/tables/table3_typologies.md) / [TeX](file:///d:/Hackathon/HB/research/tables/table3_typologies.tex)).
4. **Table 4**: Matched operating points: Validation-calibrated thresholds vs. achieved test-set precision, recall, F1, and FPR trade-offs ([MD](file:///d:/Hackathon/HB/research/tables/table4_matched_operating_points.md) / [TeX](file:///d:/Hackathon/HB/research/tables/table4_matched_operating_points.tex)).
5. **Table 5**: Multi-seed robustness evaluation reporting mean and standard deviation across 10 independent dataset realizations ([MD](file:///d:/Hackathon/HB/research/tables/table5_multi_seed_robustness.md) / [TeX](file:///d:/Hackathon/HB/research/tables/table5_multi_seed_robustness.tex)).

---

## 3. Verified Empirical Findings & Discrepancy Resolutions

1. **Exact Test-Partition Identity Reconciled**:
   - Total test transactions: $N = 295$
   - Ground-truth positives (suspicious): $P = 118$ ($\text{TP} + \text{FN} = 118$)
   - Ground-truth negatives (benign): $N_{\text{neg}} = 177$ ($\text{TN} + \text{FP} = 177$)
   - Total evaluated sum: $118 + 177 = 295$.

2. **Rules-Only vs. Isolation Forest vs. Hybrid Ranking**:
   - **Rules Engine** ($\tau=0.50$): $\text{TP}=7, \text{FP}=1, \text{TN}=176, \text{FN}=111$. Precision: $0.8750$, Recall: $0.0593$, F1: $0.1111$, ROC-AUC: $0.5268$, PR-AUC: $0.4282$.
   - **Isolation Forest** ($\tau=0.50$): $\text{TP}=113, \text{FP}=8, \text{TN}=169, \text{FN}=5$. Precision: $0.9339$, Recall: $0.9576$, F1: **$0.9456$**, ROC-AUC: **$0.9762$**, PR-AUC: **$0.9369$**.
   - **Graph Detector** ($\tau=0.50$): $\text{TP}=62, \text{FP}=11, \text{TN}=166, \text{FN}=56$. Precision: $0.8493$, Recall: $0.5254$, F1: $0.6492$, ROC-AUC: $0.7322$, PR-AUC: $0.6479$.
   - **Hybrid Ensemble** ($\tau=0.20$, validation-selected): $\text{TP}=117, \text{FP}=18, \text{TN}=159, \text{FN}=1$. Precision: $0.8667$, Recall: **$0.9915$**, F1: $0.9249$, ROC-AUC: $0.9574$, PR-AUC: $0.9156$.

3. **Honest Superiority Framing**:
   - The paper avoids claiming that the Hybrid Ensemble outperforms Isolation Forest across all metrics.
   - Isolation Forest provides superior pure point-anomaly ranking in tabular feature space (higher PR-AUC and ROC-AUC).
   - The Hybrid Ensemble provides decisive operational superiority by maximizing sensitivity (recall $99.15\%$, missing only $1$ transaction) and delivering higher precision ($95.65\%$ vs. $88.89\%$) in strict low-FPR regimes ($\le 3\%$) through cross-detector corroboration.

4. **Cryptographic Ledger Scope Clarification**:
   - Terminology updated from "Blockchain-Based" to "Tamper-Evident Audit Logging with Sequential SHA-256 Hash Chaining".
   - The single-node threat model is explicitly documented: the ledger mathematically detects all database row modifications, deletions, and link tampering, but lacks external BFT consensus to resist full forward re-computation by an adversary possessing unconstrained root DBA permissions.

5. **Multi-Dimensional Evaluation Separation**:
   - Detection performance (Precision, Recall, ROC-AUC, PR-AUC) is strictly separated from SAR narrative quality (automated 5-dimension rubric score $80.0/100$, zero PII leakage) and audit tamper detection ($100\%$ detection of injected mutations).

---

## 4. Test Suite and Verification Status

All 10 automated regression and integrity unit tests were executed and passed cleanly:
```text
tests/test_robustness_metrics.py::test_audit_reported_metrics_exact_consistency PASSED [ 10%]
tests/test_robustness_metrics.py::test_sar_pipeline_safety_and_rubric_quality PASSED   [ 20%]
tests/test_benchmark_integration.py::test_integration_and_audit_ledger_verification PASSED [ 30%]
tests/test_benchmark_integration.py::test_evidence_to_transaction_traceability PASSED [ 40%]
tests/test_synthetic_generator.py::test_generator_schema_and_referential_integrity PASSED [ 50%]
tests/test_synthetic_generator.py::test_seed_reproducibility PASSED                    [ 60%]
tests/test_synthetic_generator.py::test_temporal_monotonicity_and_balance_arithmetic PASSED [ 70%]
tests/test_synthetic_generator.py::test_zero_leakage_in_features_and_transactions PASSED [ 80%]
tests/test_synthetic_generator.py::test_detection_adapter_compatibility PASSED        [ 90%]
tests/test_synthetic_generator.py::test_confusion_matrix_and_class_count_assertions PASSED [100%]
============================== 10 passed in 13.60s ==============================
```

---

## 5. Final Pre-Submission Checklist

- [x] **Repository Source Inspection**: Completed across all backend, ML, graph, RAG, and audit modules.
- [x] **Discrepancy Audit & Reconciliation**: Completed and documented in [`research/paper_audit.md`](file:///d:/Hackathon/HB/research/paper_audit.md).
- [x] **Bibliographic Verification**: 18 real academic papers and official statutory standards verified in [`research/reference_audit.md`](file:///d:/Hackathon/HB/research/reference_audit.md) and [`research/references.bib`](file:///d:/Hackathon/HB/research/references.bib).
- [x] **Full Research Manuscript**: Authored in formal academic English in [`research/full_project_research_paper.md`](file:///d:/Hackathon/HB/research/full_project_research_paper.md) and [`research/full_project_research_paper.tex`](file:///d:/Hackathon/HB/research/full_project_research_paper.tex).
- [x] **Figures & Diagrams**: Figures 1 through 7 rendered as editable vector SVG and 300-DPI publication PNGs in [`research/figures/`](file:///d:/Hackathon/HB/research/figures/).
- [x] **Result Tables**: Tables 1 through 5 generated in Markdown and LaTeX in [`research/tables/`](file:///d:/Hackathon/HB/research/tables/).
- [x] **Mathematical Integrity**: All confusion matrices sum to 295 ($118+177$); all precision/recall/F1 metrics mathematically verified.
- [x] **Reproducibility Protocol**: Documented step-by-step in [`research/reproducibility.md`](file:///d:/Hackathon/HB/research/reproducibility.md).
- [x] **Threats to Validity & Limitations**: Explicitly declared (synthetic data, single-node ledger, uncalibrated anomaly scores).

The research paper and supporting artifacts are complete, fully reconciled, mathematically verified, and ready for publication submission.
