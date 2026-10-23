# API Specification

**Base URL:** `http://localhost:8000`  
**Authentication:** Bearer JWT Header (`Authorization: Bearer <token>`)  
**Interactive Docs:** `http://localhost:8000/docs` (Swagger UI)  

---

## 1. Authentication & System Health

### `GET /health`
- **Auth:** None (Public)
- **Response 200:**
```json
{
  "status": "ok",
  "service": "sar-narrative-generator",
  "timestamp": "2026-10-17T14:30:00Z"
}
```

### `POST /login`
- **Auth:** None (Public)
- **Request Body:**
```json
{
  "username": "analyst",
  "password": "password123"
}
```
- **Response 200:**
```json
{
  "access_token": "<jwt_token>",
  "token_type": "bearer",
  "username": "analyst",
  "role": "analyst"
}
```

---

## 2. AML Cases & Multi-Detector Investigation

### `GET /cases`
- **Auth:** Bearer Token
- **Description:** Returns all ingested and investigated cases ordered by risk score and updated timestamp.
- **Response 200:** Array of case summary objects.

### `POST /cases`
- **Auth:** Bearer Token
- **Description:** Ingests an incoming alert JSON, enriches 12-month historical KYC data, executes the three-detector pipeline (Rules, Isolation Forest, Network MultiGraph), aggregates risk, evaluates compliance policy, generates an explainable RAG SAR narrative (if draft eligible), and records an immutable block in the audit ledger.
- **Request Body:**
```json
{
  "alert_id": "ALERT_7821",
  "customer_id": "CUST_1001",
  "customer_name": "Arjun Malhotra",
  "account_type": "current",
  "customer_profile": "Student",
  "alert_type": "Layering",
  "transactions": {
    "transaction_count": 28,
    "total_amount": 1450000,
    "time_window_days": 3,
    "destination_country": "UAE",
    "reporting_threshold": 1000000
  },
  "pattern": "high velocity pass-through layering with rapid outbound remittance"
}
```
- **Response 200:** Complete case record including `risk_score`, `risk_level`, `final_sar`, `audit_events`, and `latest_analysis_run`.

### `GET /cases/{case_id}`
- **Auth:** Bearer Token
- **Response 200:** Case detail with narrative, evidence pack, validation checks, and latest multi-detector analysis run.

### `GET /cases/{case_id}/analysis-runs`
- **Auth:** Bearer Token
- **Description:** Retrieves all historical analysis runs associated with the case for longitudinal auditing.

### `GET /cases/{case_id}/analysis-runs/latest`
- **Auth:** Bearer Token
- **Response 200:** Most recent `AnalysisRunRecord`:
```json
{
  "run_id": "RUN_910fae1208a1",
  "case_id": "a1b2c3d4-...",
  "status": "COMPLETE",
  "snapshot_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "composite_score": 0.88,
  "risk_tier": "CRITICAL",
  "policy_action": "SAR_DRAFT_ELIGIBLE",
  "detector_results": {
    "rules_engine": { "normalized_score": 0.95, "status": "COMPLETE" },
    "isolation_forest": { "normalized_score": 0.85, "status": "COMPLETE" },
    "graph_detector": { "normalized_score": 0.89, "status": "COMPLETE" }
  },
  "findings": [...]
}
```

### `GET /analysis-runs/{run_id}`
- **Auth:** Bearer Token
- **Response 200:** Specific analysis run by ID.

### `GET /analysis-runs/{run_id}/findings`
- **Auth:** Bearer Token
- **Response 200:** Typed array of `DetectionFinding` objects with associated transaction IDs, entities, and feature values.

---

## 3. Review, Replay & Export

### `POST /cases/{case_id}/review`
- **Auth:** Bearer Token
- **Request Body:**
```json
{
  "analyst_id": "analyst",
  "decision": "APPROVE",
  "comment": "Confirmed rapid pass-through layering activity to UAE shell accounts.",
  "edited_narrative": "Updated text if analyst made revisions..."
}
```
- **Response 200:** Updated case with review decision, submitted timestamp, and character-level text diff.

### `POST /cases/{case_id}/replay`
- **Auth:** Bearer Token
- **Response 200:** Replay comparison payload confirming reproducibility against original prompt SHA-256 and model parameters.

### `GET /cases/{case_id}/export/pdf`
- **Auth:** Bearer Token
- **Response 200:** Streaming PDF download (`Content-Type: application/pdf`).

---

## 4. Cryptographic Ledger Verification

### `GET /audit/ledger/verify`
- **Auth:** Bearer Token
- **Description:** Runs the read-only hash chain verifier across all stored ledger blocks.
- **Response 200:**
```json
{
  "is_valid": true,
  "verified_count": 42,
  "first_failing_sequence": null,
  "mismatch_category": null,
  "details": "All 42 blocks successfully verified. Hash chain is unbroken.",
  "external_checkpoint_status": "DISABLED (Local DB Hash Chain Only - Single Node Demo)",
  "verified_at": "2026-10-17T14:35:10Z"
}
```
