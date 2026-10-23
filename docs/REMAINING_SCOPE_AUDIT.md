# Remaining Scope & Baseline Reconnaissance Audit

**Project:** A Hybrid Fraud Detection and Retrieval-Augmented Suspicious Activity Report (SAR) Generation Framework for Banking Systems with Blockchain-Based Audit Integrity  
**Date of Audit:** October 2026  
**Auditor:** Principal Software Architect & AML Systems Engineer  

---

## 1. Executive Summary

This reconnaissance audit reviews the current repository baseline (`HB`) against the target architecture of a hybrid, explainable AML investigation platform.

The existing codebase provides a working SAR narrative generation pipeline with:
- FastAPI backend with JWT authentication and role-based permissions (`analyst`, `manager`, `admin`).
- PostgreSQL persistence for cases and basic audit events.
- Database-backed KYC and 12-month transaction enrichment.
- Deterministic AML rule evaluation (`rules.yaml`, `rag_pipeline/rule_engine.py`).
- ChromaDB RAG retrieval over compliance guidance, typologies, and templates.
- Strict PII masking, sentence-level transaction ID evidence traceability, and post-generation compliance validation.
- Analyst review (approve/reject/edits/diffs), replay, and sanitized ReportLab PDF export.
- A functional vanilla HTML/CSS/JS analyst portal.

However, the repository currently assumes that alerts arrive pre-detected or manually uploaded as alert JSON files. To complete the target mission, the platform requires:
1. **Detection Layer B**: Unsupervised behavioral anomaly detection (Isolation Forest) with strict feature engineering and no leakage.
2. **Detection Layer C**: Graph-based laundering pattern detection (NetworkX MultiGraph) with bounded cycle detection, layering chains, rapid pass-through, and fan-in/fan-out.
3. **Common Detection Finding Contract & Versioned Composite Aggregator**: Combining rule, anomaly, and graph evidence with policy-driven decisioning (`SAR_DRAFT_ELIGIBLE`, `ANALYST_REVIEW_REQUIRED`, etc.) and explicit handling of partial/failed detectors.
4. **Tamper-Evident Hash-Chained Audit Ledger**: Upgrading the simple `audit_events` table into a cryptographically linked block/event ledger with canonical JSON serialization, SHA-256 chaining, concurrency protection, verification API/CLI, and an honest threat model.
5. **Reproducible Evaluation & Ablation Harness**: Synthetic motif generation, IBM AMLSim / synthetic benchmark runner, detector ablation study, leakage checks, and metrics reporting.
6. **Formal Architectural & Research Documentation**: Full documentation suite across architecture, threat modeling, model card, audit ledger, and API specs.

---

## 2. Baseline Test Execution Results

Executed baseline test suite using Python 3.12 in `.venv`:
```bash
.venv\Scripts\python.exe -m pytest -q
```
**Results:** `1 failed, 34 passed, 4 warnings in 43.47s`

### Baseline Failure Details:
- **Test:** `tests/test_backend.py::test_enrich_narrative_with_pii_replaces_case_insensitive_terms`
- **Root Cause:** The test asserted that `Rohit Sharma` (the customer name) should appear in `enriched`. However, `backend/app.py::enrich_narrative_with_pii()` intentionally enforces a strict PII defense-in-depth policy where raw customer names are stripped and replaced with generic tokens (`the account holder`). The test expectation was outdated with respect to the PII safety hardening in `app.py`.
- **Treatment:** Correct the test expectation to match the safety invariant (verifying that placeholder structures are enriched while customer names remain protected).

---

## 3. Detailed Scope & Gap Inventory Table

| # | Capability | Evidence File / Function / API | Current Status | Risk / Impact | Proposed Treatment |
|---|---|---|---|---|---|
| 1 | **Alert & Case Intake** | `backend/app.py` (`POST /cases`), `backend/schemas.py` (`AlertPayload`), `backend/database.py` (`cases` table) | **Implemented** | Low. Existing contract works for alert JSON uploads. Lacks analysis run versioning, frozen snapshots, and idempotency keys. | Keep existing `POST /cases` backwards-compatible. Add `AnalysisRun` / `DetectionRun` models, snapshot hashing, and idempotency support. |
| 2 | **Database Enrichment (KYC & 12M Txns)** | `backend/enrichment.py` (`enrich_case`), `backend/database.py` (`Customer`, `Account`, `Transaction`) | **Implemented** | Low. Enriches 12-month baselines, inflow deviation, and counterparty counts. | Preserve and feed into feature extractors for anomaly detection and graph construction. |
| 3 | **Detection Layer A (Deterministic Rules)** | `rules.yaml`, `rag_pipeline/rule_engine.py` (`evaluate_rules`, `calculate_risk_score`) | **Implemented** | Medium. Rules work well but output internal dictionaries rather than a standardized, typed `DetectionFinding` contract. | Wrap rule outputs in a typed `DetectionFinding` adapter; validate YAML configuration at startup with schema enforcement. |
| 4 | **Detection Layer B (Behavioral Isolation Forest)** | *None* | **Missing** | High. System currently lacks behavioral anomaly detection for unconfigured or novel deviations. | Implement `ml/anomaly_detector.py` with deterministic feature builder (rolling amounts, counts, velocities, deviations), scikit-learn IsolationForest, model versioning/hashing, and documented score normalization. |
| 5 | **Detection Layer C (Graph Pattern Detection)** | *None* | **Missing** | High. System cannot detect complex topological laundering topologies (circular flows, layering chains, fan-in/fan-out, pass-through). | Implement `graph/graph_detector.py` using NetworkX directed MultiGraph with bounded cycle exploration, temporal path limits, computation budgets, and exact edge/transaction traceability. |
| 6 | **Composite Aggregator & Policy Engine** | `rag_pipeline/rule_engine.py` (basic confidence average) | **Partial** | High. Simple arithmetic mean of rule confidence. Lacks multi-detector weighting, partial execution handling, and policy-driven escalation. | Implement `detection/aggregator.py` and `detection/policy.py`. Define configurable weights, handle `FAILED`/`INSUFFICIENT_DATA` without defaulting to zero, and produce structured policy actions (`SAR_DRAFT_ELIGIBLE`, etc.). |
| 7 | **SAR RAG Narrative & Traceability** | `rag_pipeline/pipeline_service.py` (`SarRagService`), `sar_safety.py` | **Implemented** | Low. High quality 5-paragraph JSON generation with real transaction ID linkage and PII leak detection. | Preserve completely. Connect upstream to policy engine so drafting only triggers when policy marks case as draft eligible. |
| 8 | **Analyst Review & PDF Export** | `backend/app.py` (`POST /cases/{id}/review`, `GET /cases/{id}/export/pdf`) | **Implemented** | Low. Review workflow with diff tracking and sanitized ReportLab PDF export works reliably. | Preserve existing endpoints. Add detection findings and audit verification metadata to PDF generation where appropriate. |
| 9 | **Tamper-Evident Hash-Chained Audit Ledger** | `backend/database.py` (`audit_events` table) | **Partial** | High. Current audit table is standard SQL append without block hashing, previous-link SHA-256 hashes, or verification checks. | Implement `audit/ledger.py` with canonical JSON serialization, sequential chaining (`prev_hash` -> `block_hash`), concurrency control, verification CLI/API, and honest threat model documentation. |
| 10 | **Evaluation & Reproducibility Harness** | *None* | **Missing** | Medium. Project relies on a single seed case (`alert_case.json`). Lacks benchmark datasets, motif generators, or ablation studies. | Build `evaluation/` with synthetic motif generator, benchmark dataset tooling, leakage checks, detector ablation harness, and Markdown/JSON report generators. |
| 11 | **Analyst UI Integration** | `frontend/` (`dashboard.html`, `review.html`, `new_case.html`, `audit.html`, `api.js`) | **Partial** | Medium. UI only shows rule-based SAR review and basic audit list. | Add detector contribution breakdowns, graph findings, partial analysis warnings, and ledger verification status to the frontend. |
| 12 | **Documentation Suite** | `README.md`, `SYSTEM_WORKING.md`, `IMPLEMENTED_SCOPE.md` | **Partial** | Low. Existing docs focus on SAR generation. | Create complete suite in `docs/`: `ARCHITECTURE.md`, `THREAT_MODEL.md`, `MODEL_CARD.md`, `EVALUATION_PROTOCOL.md`, `AUDIT_LEDGER.md`, `API.md`. |

---

## 4. Execution Plan by Phase

- **Phase 1: Contracts and Persistence**
  - Implement typed models in `detection/contracts.py`: `AnalysisSnapshot`, `DetectionFinding`, `DetectorStatus`, `AnalysisRun`, `CompositeScore`, `PolicyDecision`.
  - Add SQLAlchemy models and database persistence for `analysis_runs` and `detection_findings`.
- **Phase 2: Detector Adapters & Behavioral Anomaly Detection**
  - Standardize `rule_engine.py` with a rule adapter.
  - Implement deterministic feature engineering (`ml/features.py`) and Isolation Forest training/inference/versioning (`ml/anomaly_detector.py`).
- **Phase 3: Graph-Based AML Pattern Detection**
  - Implement directed MultiGraph builder and bounded detectors (`graph/graph_detector.py`): rapid pass-through, layering chains, bounded circular flows, fan-in/fan-out, with execution and budget limits.
- **Phase 4: Hybrid Aggregation & Policy Engine**
  - Implement `detection/aggregator.py` and `detection/policy.py`. Support configurable weights, reason codes, and policy states.
- **Phase 5: Tamper-Evident Hash-Chained Audit Ledger**
  - Implement `audit/ledger.py`: canonical envelope, SHA-256 block hashing, atomic append, verification engine, and CLI verifier.
- **Phase 6: Integration, API & UI**
  - Integrate multi-detector pipeline into `backend/app.py`.
  - Connect policy engine to existing `SarRagService`.
  - Enhance frontend dashboard and review views.
- **Phase 7: Evaluation, Hardening & Documentation**
  - Implement synthetic motif dataset generator, ablation study, and test suite.
  - Write full documentation suite in `docs/`.

---

## 5. Final Verification & Post-Implementation Status

All capabilities identified as missing or partial in the baseline audit have been implemented, integrated, and verified against automated tests:

| Capability | Initial Baseline | Final Status | Verification Evidence |
|---|---|---|---|
| **Intake Snapshot & Hashing** | Missing | **Implemented** | `detection/snapshot.py`, unit tested in `tests/test_detection_framework.py` |
| **Rule Engine Adapter** | Partial | **Implemented** | `detection/rules_adapter.py`, integrated in `MultiDetectorService` |
| **Isolation Forest Anomaly Layer** | Missing | **Implemented** | `ml/features.py`, `ml/anomaly_detector.py`, verified with leakage tests |
| **NetworkX MultiGraph Detector** | Missing | **Implemented** | `graph/graph_detector.py`, bounded cycles, pass-through, and hub detection |
| **Hybrid Aggregator & Policy** | Partial | **Implemented** | `detection/aggregator.py`, `detection/policy.py`, weight validation tests |
| **Tamper-Evident Hash Ledger** | Partial | **Implemented** | `audit/ledger.py`, `scripts/verify_audit_ledger.py --demo` verified |
| **Analysis Run Endpoints** | Missing | **Implemented** | `GET /cases/{id}/analysis-runs`, `GET /audit/ledger/verify` in `app.py` |
| **Evaluation & Ablation Harness** | Missing | **Implemented** | `evaluation/evaluator.py`, `reports/evaluation_report.md` generated |
| **Analyst UI Integration** | Partial | **Implemented** | `frontend/audit.html` (ledger status), `frontend/review.html` (findings) |
| **Documentation Suite** | Partial | **Implemented** | `docs/ARCHITECTURE.md`, `THREAT_MODEL.md`, `MODEL_CARD.md`, `EVALUATION_PROTOCOL.md`, `AUDIT_LEDGER.md`, `API.md` |

**Automated Test Suite Status:** `46 passed, 0 failed, 4 warnings in 37.59s` (100% passing).

