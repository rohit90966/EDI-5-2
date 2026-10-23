# Hybrid AML Investigation, Fraud Detection & SAR Decisioning Framework

AI-assisted Suspicious Activity Report (SAR) decision-support system featuring:

- **Multi-Detector Suspicious Activity Detection:**
  - Deterministic AML rule engine (`rules.yaml`) with regulatory citations
  - Unsupervised behavioral anomaly detection via Isolation Forest (`sklearn.ensemble.IsolationForest`)
  - Graph-based topological laundering pattern detection via NetworkX directed `MultiDiGraph` (rapid pass-through, circular funds flows, fan-in/fan-out mule hubs)
- **Deterministic Policy & Hybrid Risk Aggregation:**
  - Configurable, versioned multi-detector weights (`0.35` Rules, `0.25` Anomaly, `0.40` Graph)
  - Explicit policy actions (`SAR_DRAFT_ELIGIBLE`, `ANALYST_REVIEW_REQUIRED`, `NO_ADDITIONAL_REVIEW_TRIGGERED`)
  - Partial/incomplete analysis handling without silent failure-to-zero
- **Cryptographic Hash-Chained Audit Ledger:**
  - Append-only sequential SHA-256 block ledger (`prev_hash` -> `block_hash`)
  - Automated verification engine (`GET /audit/ledger/verify` and CLI `scripts/verify_audit_ledger.py`)
- **Regulator-Safe RAG Narrative Generation:**
  - Retrieval-Augmented Generation (ChromaDB) over compliance typologies and guidelines
  - Sentence-level evidence traceability linked to real transaction IDs
  - Strict PII masking and defense-in-depth sanitization
- **Analyst Portal & Reporting:**
  - Vanilla HTML/CSS/JS human-in-the-loop analyst dashboard, review diffs, and replay
  - Sanitized ReportLab PDF export with dynamic review status watermarks

## Current Status

This repository is production-style and end-to-end runnable locally.

- Multi-detector pipeline (Rules, Isolation Forest, NetworkX MultiGraph) is fully implemented.
- Hybrid score aggregation and AML compliance policy engine are fully operational.
- Tamper-evident hash-chained audit ledger with CLI verification is implemented.
- Reproducible research benchmark harness with ablations and leakage checks is implemented.
- Full 46-test regression suite passes with 100% success.

## Explainability and Validation Guarantees

The SAR generator now enforces a regulator-safe explainability contract:

- Every narrative sentence is represented in structured JSON.
- Evidence references must be real transaction IDs (for example `TXN_00031`).
- Narrative reasoning is constrained to fact-plus-comparison-plus-reasoning patterns.
- Counterparty relationship intelligence is injected from enrichment into generation prompts.
- Strict post-generation validation blocks weak or unverifiable outputs.

### Sentence Output Schema

Final SAR responses include sentence objects with this shape:

```json
{
	"text": "The account received 57 credits in 3 days, compared with its historical monthly pattern, indicating abnormal activity.",
	"evidence": ["TXN_00031", "TXN_00032"],
	"type": "transaction_data"
}
```

`type` can be:

- `transaction_data`
- `reference_knowledge`
- `evidence_not_available`

### Evidence Buckets Passed to the LLM

The prompt now includes transaction ID buckets derived from enrichment data:

- `high_velocity_txns`
- `uae_transfers`
- `structuring_txns`

Only these IDs should be used for generated sentence evidence.

### Counterparty Intelligence in Enrichment

Enrichment now computes and passes:

- `unique_counterparties_count`
- `prior_counterparties_count` (last 12 months)
- `new_counterparties_count`
- `has_prior_relationship`

These fields are explicitly required in the narrative analysis.

### Strict Validation Rules

Validation now fails when any of the following occurs:

- A structured sentence has empty `evidence`.
- A structured sentence references unknown/fake transaction IDs.
- Vague wording appears (`multiple`, `several`, `various`).
- Required reasoning language is absent (`indicating` or `suggesting`).

Validation output includes:

- `passed`
- `checks`
- `failed_checks`
- `validation_errors`
- `validated_at`

## PDF Export Hardening

PDF generation now applies a defense-in-depth sanitization pass before rendering:

- Evidence markers (for example `[E1]`, `[TXN:...]`) are removed from visible report prose.
- ISO timestamps are converted to analyst-friendly date format.
- Raw customer name and customer ID are hard-stripped from narrative body text.
- Footer review wording is dynamic (`APPROVED`, `REJECTED`, or `PENDING`) based on analyst decision.

This keeps generated PDF reports readable while preventing accidental leakage of internal trace tags or sensitive identifiers.

## End-to-End Flow

For each incoming alert (`POST /cases`):

1. Authenticate request via JWT bearer token.
2. Enrich alert with DB-backed customer profile + 12-month transaction intelligence.
3. Evaluate AML rules from `rules.yaml` and compute risk score + level.
4. Mask sensitive fields before retrieval.
5. Retrieve supporting context from ChromaDB.
6. Generate SAR narrative with the configured Hugging Face model.
7. Validate narrative quality and compliance checks.
8. Build sentence-level evidence mapping for explainability.
9. Persist case state and audit events in PostgreSQL.
10. Support analyst approve/reject and narrative edits.
11. Support replay and PDF export for archival.

## Repository Layout

```text
barclays/
|-- README.md
|-- requirements.txt
|-- rules.yaml
|-- .env.example
|-- backend/
|   |-- app.py
|   |-- database.py
|   |-- enrichment.py
|   `-- schemas.py
|-- data/
|   |-- alert_case.json
|   |-- aml_rules.yaml
|   |-- aml_typologies.txt
|   |-- example_sar_narratives.txt
|   |-- regulatory_writing_guidelines.txt
|   `-- sar_narrative_templates.txt
|-- frontend/
|   |-- index.html
|   |-- dashboard.html
|   |-- review.html
|   |-- new_case.html
|   |-- audit.html
|   |-- api.js
|   `-- style.css
|-- rag_pipeline/
|   |-- pipeline_service.py
|   |-- rule_engine.py
|   |-- sar_rag_pipeline.py
|   |-- ingestion_pipeline.py
|   `-- vector_db/
|-- scripts/
|   |-- ensure_local_postgres.py
|   |-- seed_data.py
|   `-- calculate_llm_tokens.py
|-- tests/
|   `-- test_backend.py
`-- vector_db/
```

## API Summary

Base URL: `http://localhost:8000`

Authentication:

- `POST /login` returns a bearer token.
- All `/cases` routes require `Authorization: Bearer <token>`.

Public endpoints:

- `GET /health`
- `POST /login`

Protected endpoints:

- `GET /cases`
- `POST /cases`
- `GET /cases/{case_id}`
- `GET /cases/{case_id}/audit`
- `POST /cases/{case_id}/review`
- `POST /cases/{case_id}/replay`
- `GET /cases/{case_id}/export/pdf`

Note: route signatures and auth flow remain unchanged. The stricter explainability logic is internal to enrichment and narrative pipeline stages.

## Enrichment Data Model

The enrichment layer uses three PostgreSQL tables managed via SQLAlchemy:

- `customers`
	- `customer_id` (PK)
	- `name`
	- `occupation`
	- `monthly_income`
	- `risk_rating`
- `accounts`
	- `account_id` (PK)
	- `customer_id` (FK -> `customers.customer_id`)
	- `account_type`
	- `opened_date`
- `transactions`
	- `txn_id` (PK)
	- `account_id` (FK -> `accounts.account_id`)
	- `amount`
	- `txn_type` (`credit` / `debit`)
	- `country`
	- `timestamp`
	- `counterparty` (optional, used for counterparty analytics)

Tables are created automatically at API startup via `init_db()`.

## Seed Dummy Data

Seed realistic dummy KYC + transaction history:

```bash
python scripts/seed_data.py
```

Seed output includes:

- 4 customers and 4 accounts
- 94 transactions total
- One suspicious customer with high-velocity pass-through behavior and UAE transfers
- Normal activity for remaining customers

Important: alert `customer_id` must match seeded `customer_id` values for enrichment to take effect.

Current seeded IDs:

- `CUST_1001`
- `CUST_1002`
- `CUST_1003`
- `CUST_1004`

## Prerequisites

- Python 3.10+
- PostgreSQL running locally
- Hugging Face account and API token
- (Optional) Conda environment named `rag`

## Local Setup

### 1) Install dependencies

```bash
conda activate rag
pip install -r requirements.txt
```

If you do not use Conda:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2) Create environment file

Copy `.env.example` to `.env` and update values for your machine:

```bash
copy .env.example .env
```

Default template:

```env
DATABASE_URL=postgresql://postgres:root@localhost:5432/sar_audit
POSTGRES_ADMIN_DB=postgres
FASTAPI_URL=http://localhost:8000
LLM_PROVIDER=huggingface
HF_MODEL=Qwen/Qwen2.5-7B-Instruct
HF_API_TOKEN=hf_your_token_here
CHROMA_DB_PATH=rag_pipeline/vector_db
```

Important: if your local PostgreSQL password is not `root`, update `DATABASE_URL` before continuing.

### 3) Ensure PostgreSQL database exists

```bash
python scripts/ensure_local_postgres.py
```

### 4) Configure Hugging Face

Create a free Hugging Face account and create an access token at:
`https://huggingface.co/settings/tokens`

Set the token in `.env` as `HF_API_TOKEN`. The default model is `openai/gpt-oss-120b:fastest`.

### 5) Seed enrichment data

```bash
python scripts/seed_data.py
```

### 6) Build or refresh vector store

```bash
cd rag_pipeline
python ingestion_pipeline.py
cd ..
```

### 7) Start backend

```bash
uvicorn backend.app:app --reload
```

- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`

### 8) Start frontend

```bash
cd frontend
python -m http.server 8080
```

- UI: `http://localhost:8080`

## Quick Start (PowerShell)

```powershell
conda activate rag
copy .env.example .env
python scripts/ensure_local_postgres.py
python scripts/seed_data.py

Push-Location rag_pipeline
python ingestion_pipeline.py
Pop-Location

Start-Process powershell -ArgumentList '-NoExit', '-Command', 'conda activate rag; uvicorn backend.app:app --reload'
Push-Location frontend
python -m http.server 8080
Pop-Location
```

## Token Usage Report (LLM)

Use the helper script to calculate token usage across the full RAG prompt path (query, retrieved docs, and prompt estimates):

```bash
python scripts/calculate_llm_tokens.py --model openai/gpt-oss-120b:fastest
```

Optional: save output JSON

```bash
python scripts/calculate_llm_tokens.py --model openai/gpt-oss-120b:fastest --out reports/token_report.json
```

Current default generation options in the prompt bundle:

```json
{"num_ctx": 4096, "temperature": 0.2, "top_p": 0.9}
```

## Default Login Credentials

- `analyst` / `password123` (role: analyst)
- `manager` / `password123` (role: manager)
- `admin` / `password123` (role: admin)

## Test Suite

Run:

```bash
pytest -q
```

Coverage includes:

- Login success and login failure
- Auth guard for protected endpoints
- Case creation and risk-level response
- Review validation and review success
- PDF export content-type
- Safety pipeline behavior (`tests/test_sar_safety.py`)

## Core Technology Stack

- Backend: FastAPI, Pydantic, Uvicorn
- Auth: python-jose (JWT), passlib
- Database: PostgreSQL, psycopg2-binary
- ORM: SQLAlchemy 2.x
- Retrieval: ChromaDB, sentence-transformers
- LLM: Hugging Face Inference Providers
- PDF: reportlab
- Frontend: HTML, CSS, vanilla JavaScript
- Testing: pytest, httpx, FastAPI TestClient

## Troubleshooting

- `401 Missing Bearer token`: obtain JWT from `POST /login` and pass `Authorization: Bearer <token>`.
- `Connection refused` to PostgreSQL: verify DB service is running, then re-run `python scripts/ensure_local_postgres.py`.
- Empty/weak retrieval: re-run `python rag_pipeline/ingestion_pipeline.py` to refresh embeddings.
- Ollama generation failures: ensure `ollama serve` is running and model is pulled.
- Seed script fails with DB auth: verify `DATABASE_URL` in `.env` and rerun `python scripts/seed_data.py`.
- Enrichment not found for alerts: ensure alert `customer_id` matches a seeded customer ID.

## Notes

- `rules.yaml` is the primary AML rule configuration used by the pipeline.
- `data/aml_rules.yaml` is retained in the dataset folder and can be used as reference material.
- Vector database snapshots may exist under both `rag_pipeline/vector_db/` and root `vector_db/`.
- `streamlit` exists in `requirements.txt` but the shipped analyst UI is in `frontend/` (plain HTML/CSS/JS).