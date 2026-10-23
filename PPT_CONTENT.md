# PPT Content: SAR Narrative Generator

## Presentation Title

**A Hybrid AML Alert Review and Retrieval-Augmented SAR Narrative Generator**

### Subtitle

Implemented project milestone: deterministic AML detection, transaction enrichment, RAG-assisted drafting, explainability, analyst review, and audit-ready PDF export.

### Team and Project Information

- Department: Computer Engineering
- Academic year: 2026-27
- Project area: Artificial Intelligence, AML compliance, FinTech, and Natural Language Generation
- Current milestone: End-to-end local prototype

---

## Slide 1: Problem Statement

### On-slide content

Financial institutions must investigate suspicious transaction alerts and prepare Suspicious Activity Reports. The current review process is difficult because:

- Static thresholds do not provide enough behavioral context.
- Analysts must manually compare current activity with historical customer behavior.
- SAR narratives require precise regulatory language and evidence.
- Generated text can expose PII, invent figures, or lose traceability.
- Review decisions and edits need a reproducible audit history.

### Speaker note

The project addresses the practical gap between alert detection and regulator-ready narrative preparation. The implemented milestone focuses on a complete analyst workflow rather than only an isolated language model demo.

---

## Slide 2: Project Objective

### On-slide content

Build a local AML case-processing system that can:

1. Receive a suspicious activity alert.
2. Enrich it with KYC and transaction history.
3. Apply explainable AML rules.
4. Retrieve relevant compliance knowledge.
5. Generate a structured SAR narrative.
6. Validate evidence, numbers, wording, and privacy.
7. Let an analyst review, edit, approve, reject, replay, audit, and export the case.

### Current implementation boundary

The current repository implements the SAR review workflow. Blockchain anchoring and graph-based multi-account fraud analysis remain future extensions from the larger project vision.

---

## Slide 3: Implemented Solution at a Glance

```text
 +-------------+      +----------------+      +------------------+
 | Alert JSON  | ---> | FastAPI API    | ---> | Case Orchestrator|
 +-------------+      | JWT Protected  |      +---------+--------+
                      +----------------+                |
                                                       v
              +------------------+       +------------------------+
              | PostgreSQL       | <---- | KYC and Txn Enrichment |
              | Cases and Audit  |       +------------------------+
              +------------------+                |
                                                       v
              +------------------+       +------------------------+
              | YAML AML Rules   | --->  | Risk Score and Evidence |
              +------------------+       +------------------------+
                                                       |
                                                       v
              +------------------+       +------------------------+
              | ChromaDB +       | --->  | Ollama SAR Generation  |
              | Embeddings       |       +------------------------+
              +------------------+                |
                                                       v
              +------------------+       +------------------------+
              | Validation and   | --->  | Analyst Review and PDF  |
              | Traceability     |       +------------------------+
              +------------------+
```

### Key message

The system combines deterministic controls and generative AI. Rules decide what was flagged; RAG supplies writing and regulatory context; validation controls what can proceed to analyst review.

---

## Slide 4: System Architecture

```text
                         +-----------------------+
                         | Analyst Browser UI    |
                         | HTML/CSS/JavaScript   |
                         +-----------+-----------+
                                     |
                             HTTP + JWT bearer
                                     |
                         +-----------v-----------+
                         | FastAPI Backend       |
                         | app.py                |
                         +--+-----+-----+--------+
                            |     |     |
              +-------------+     |     +----------------+
              |                   |                      |
      +-------v-------+   +-------v-------+      +-------v-------+
      | Authentication|   | Case Pipeline |      | PDF Builder   |
      | JWT            |   | SarRagService|      | ReportLab      |
      +---------------+   +---+-------+---+      +---------------+
                              |       |
                 +------------+       +-------------+
                 |                                  |
         +-------v-------+                  +-------v-------+
         | Rule Engine   |                  | RAG and LLM   |
         | rules.yaml    |                  | Chroma +      |
         | Risk scoring  |                  | Ollama        |
         +---------------+                  +-------+-------+
                                                   |
                                           +-------v-------+
                                           | Validation,   |
                                           | Evidence,     |
                                           | Traceability  |
                                           +---------------+

         +----------------------+       +----------------------+
         | PostgreSQL           |       | ChromaDB             |
         | Customers            |       | sar_knowledge        |
         | Accounts             |       | Compliance corpus    |
         | Transactions         |       +----------------------+
         | Cases and Audit      |
         +----------------------+
```

### Components

- Frontend: static analyst console.
- API: FastAPI routes and lifecycle orchestration.
- Persistence: PostgreSQL with SQLAlchemy and JSONB case artifacts.
- Detection: YAML-driven deterministic AML rules.
- Retrieval: ChromaDB and `all-MiniLM-L6-v2` embeddings.
- Generation: local Ollama model.
- Export: ReportLab PDF generation.

---

## Slide 5: End-to-End Processing Flow

```text
 1. Alert submitted
        |
        v
 2. Pydantic schema validation
        |
        v
 3. Customer and account lookup
        |
        v
 4. Twelve-month transaction enrichment
        |
        v
 5. Mask name and customer ID
        |
        v
 6. Evaluate AML rules from rules.yaml
        |
        +---- no rule fired ----> NO_SAR_REQUIRED
        |
        v
 7. Calculate risk score and risk level
        |
        v
 8. Build RAG query from rules and alert pattern
        |
        v
 9. Retrieve compliance context from ChromaDB
        |
        v
10. Build strict JSON prompt
        |
        v
11. Generate five-part narrative with Ollama
        |
        v
12. Validate PII, evidence, numbers, format, and filing language
        |
        v
13. Build sentence-level traceability
        |
        v
14. Persist case and audit events
        |
        v
15. Analyst review, replay, and PDF export
```

---

## Slide 6: Alert Input and Enrichment

### Alert input

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
    "destination_country": "UAE"
  },
  "pattern": "high velocity pass-through layering"
}
```

### Enrichment outputs

- Historical average credit inflow over twelve months.
- Alert-window transaction count and inflow.
- Deviation from the historical baseline.
- Dominant destination country.
- Unique, prior, and new counterparties.
- Real transaction IDs for evidence references.
- Customer occupation, income, and risk rating.

### Why it matters

An alert is evaluated against customer context instead of being treated as an isolated transaction summary.

---

## Slide 7: Database Architecture

```text
 +------------------+
 | customers        |
 |------------------|
 | customer_id (PK) |
 | name             |
 | occupation       |
 | monthly_income   |
 | risk_rating      |
 +--------+---------+
          | 1
          |
          | many
 +--------v---------+
 | accounts         |
 |------------------|
 | account_id (PK)  |
 | customer_id (FK) |
 | account_type     |
 | opened_date      |
 +--------+---------+
          | 1
          |
          | many
 +--------v---------+
 | transactions     |
 |------------------|
 | txn_id (PK)      |
 | account_id (FK)  |
 | amount           |
 | txn_type         |
 | country          |
 | timestamp        |
 | counterparty     |
 +------------------+

 +------------------+       +------------------+
 | cases            | 1   * | audit_events    |
 |------------------|------>|------------------|
 | case_id (PK)     |       | event_id (PK)    |
 | alert_payload    |       | case_id (FK)     |
 | masked_payload   |       | event_type       |
 | evidence_pack    |       | event_payload    |
 | final_sar        |       | created_at       |
 | analyst_review   |       +------------------+
 +------------------+
```

### Persistence approach

- SQLAlchemy manages enrichment entities.
- Direct PostgreSQL JSONB storage preserves complete pipeline artifacts.
- Audit events are ordered by timestamp and event ID.

---

## Slide 8: Deterministic AML Rule Engine

### Rule evaluation model

```text
 Alert fields + derived fields + YAML thresholds
                       |
                       v
             +---------------------+
             | Condition evaluator |
             +----------+----------+
                        |
                        v
             +---------------------+
             | Triggered evidence  |
             | blocks              |
             +----------+----------+
                        |
                        v
             +---------------------+
             | Average confidence |
             +----------+----------+
                        |
                        v
             +---------------------+
             | Risk score + level  |
             +---------------------+
```

### Implemented rule categories

- Structuring and smurfing.
- High velocity.
- Large-value activity.
- Profile inconsistency.
- High-risk jurisdiction.
- Rapid fund movement and layering.
- Deposit aggregation and transfer patterns.
- Round tripping and cash-intensive activity.
- Multi-account layering.
- Account type mismatch.

### Risk classification

```text
 Average confidence >= 0.80  -> HIGH
 Average confidence >= 0.60  -> MEDIUM
 Average confidence >  0.00  -> LOW
 No triggered rules           -> LOW / NO_SAR_REQUIRED path
```

---

## Slide 9: RAG Knowledge Pipeline

```text
 +-------------------------+
 | Compliance text corpus  |
 | Typologies              |
 | Guidelines              |
 | Templates               |
 | Example SARs            |
 +------------+------------+
              |
              v
 +-------------------------+
 | Document type detection |
 +------------+------------+
              |
              v
 +-------------------------+
 | Smart chunking          |
 | Paragraph/delimiter     |
 +------------+------------+
              |
              v
 +-------------------------+
 | Metadata and hash       |
 | Deduplication           |
 +------------+------------+
              |
              v
 +-------------------------+
 | Sentence Transformer    |
 | all-MiniLM-L6-v2        |
 +------------+------------+
              |
              v
 +-------------------------+
 | ChromaDB collection     |
 | sar_knowledge           |
 +-------------------------+
```

### Runtime retrieval

- Build a query from fired rule names, observations, alert pattern, and alert type.
- Embed the query using the same embedding model.
- Retrieve the three closest documents.
- Record IDs, scores, metadata, and corpus snapshot.
- Limit retrieved chunks before prompt construction.

---

## Slide 10: LLM Prompt and Narrative Generation

### Prompt contract

The local Ollama model is instructed to return strict JSON:

```json
{
  "paragraphs": [
    "Background...",
    "Transaction Summary...",
    "Typology...",
    "Evidence...",
    "Conclusion..."
  ],
  "sentences": [
    {
      "sentence": "Fact compared with baseline, indicating abnormal activity.",
      "evidence": ["TXN_00031"],
      "type": "transaction_data"
    }
  ]
}
```

### Generation constraints

- Exactly five paragraphs.
- Exact numbers from the alert and enrichment data.
- Real transaction IDs only.
- No raw customer name or customer ID.
- Fact plus comparison plus reasoning structure.
- Explicit SAR filing statement with FIU reference.
- No vague terms such as “multiple”, “several”, or “various”.

---

## Slide 11: Explainability and Evidence Traceability

```text
 +--------------------+
 | Narrative sentence |
 +---------+----------+
           |
           v
 +--------------------+
 | Evidence reference |
 | TXN_00031          |
 +---------+----------+
           |
           +------------------+
           |                  |
           v                  v
 +--------------------+  +--------------------+
 | Enriched transaction|  | Rule or RAG source |
 | amount, date,       |  | AML-001 or document|
 | country, counterparty|  +--------------------+
 +--------------------+
```

### Structured evidence types

- `transaction_data`: sentence supported by real transaction IDs.
- `reference_knowledge`: sentence linked to retrieved compliance material.
- `evidence_not_available`: fallback state requiring analyst attention.

### Analyst value

The reviewer can inspect why a sentence exists and which transaction or rule supports it, rather than receiving an opaque generated paragraph.

---

## Slide 12: Safety and Validation Layer

```text
                 Generated narrative
                         |
                         v
              +-----------------------+
              | PII validation        |
              | Name and customer ID  |
              +-----------+-----------+
                          |
                          v
              +-----------------------+
              | Structure validation  |
              | Five paragraphs       |
              +-----------+-----------+
                          |
                          v
              +-----------------------+
              | Evidence validation   |
              | Real TXN IDs           |
              +-----------+-----------+
                          |
                          v
              +-----------------------+
              | Content validation     |
              | Numbers, typology,     |
              | filing language        |
              +-----------+-----------+
                          |
                 +--------+--------+
                 |                 |
                 v                 v
        PASS / REVIEW READY   CHECK FAIL / REVIEW FLAG
```

### Additional protection

- Prompt-time masking prevents direct identity exposure to the model.
- A PII failure is a hard processing block; other failed checks are stored in the validation payload for analyst review.
- Post-generation processing removes placeholders and PII.
- PDF export removes evidence tags and raw identity data from narrative prose.
- The standalone `sar_safety.py` module provides retry, evidence-anchor checks, and structured safety violations.

---

## Slide 13: Analyst User Interface

```text
 +----------+     +-------------+     +--------------+
 | Login    | --> | Dashboard   | --> | New Case     |
 +----------+     +------+------+     +------+-------+
                        |                     |
                        |                     v
                        |              +------+-------+
                        |              | Upload alert |
                        |              | Preview JSON |
                        |              +------+-------+
                        |                     |
                        +---------------------+
                                              v
                                    +---------+----------+
                                    | Case Review        |
                                    | Rules              |
                                    | Editable narrative|
                                    | Validation checks |
                                    +----+---------+-----+
                                         |         |
                            +------------+         +-------------+
                            v                                    v
                    +-------+--------+                   +-------+--------+
                    | Approve/Reject|                   | Replay Diff    |
                    +-------+--------+                   +----------------+
                            |
                            v
                    +-------+--------+       +----------------+
                    | Audit Timeline|       | PDF Export     |
                    +----------------+       +----------------+
```

### Implemented screens

- Login.
- Dashboard with case counts, risk levels, status, SLA age, and actions.
- New case upload and preview.
- Case review with editable narrative sections.
- Validation results and sentence-level explainability styling.
- Replay comparison.
- Audit event timeline.

---

## Slide 14: Review, Audit, and Export

### Review lifecycle

```text
 PENDING_ANALYST_REVIEW
          |
          +--> Analyst edits narrative
          |
          +--> Mandatory comment
          |
          +--> APPROVE -> APPROVED -> local export ready
          |
          +--> REJECT  -> REJECTED
```

### Stored review information

- Analyst ID.
- Decision.
- Comment.
- Submission timestamp.
- Whether the narrative was edited.
- Line-level text diff between generated and edited narrative.

### PDF report contents

- Case and alert metadata.
- Risk score and triggered rule table.
- Narrative sections.
- Analyst decision and comment.
- Prompt hash, model, temperature, corpus snapshot, and pipeline version.
- Dynamic footer showing approved, rejected, or pending state.

---

## Slide 15: API Demonstration Flow

```text
 POST /login
      |
      v
 Authorization: Bearer <token>
      |
      v
 POST /cases
      |
      v
 GET /cases/{id}
      |
      +--> GET /cases/{id}/audit
      |
      +--> POST /cases/{id}/review
      |
      +--> POST /cases/{id}/replay
      |
      +--> GET /cases/{id}/export/pdf
```

### API highlights

- Protected case routes require a bearer token.
- Case responses include audit events.
- Review requests require a comment of at least ten characters.
- PDF responses are streamed as `application/pdf`.
- Missing or invalid cases return HTTP 404.
- Missing or invalid authentication returns HTTP 401.

---

## Slide 16: Technology Stack

| Layer | Technology | Role |
| --- | --- | --- |
| Frontend | HTML, CSS, JavaScript | Analyst workflow |
| API | FastAPI, Uvicorn | HTTP services |
| Validation | Pydantic | Alert and review contracts |
| Authentication | JWT with `python-jose` | Demo bearer authentication |
| Database | PostgreSQL | Enrichment, cases, audit |
| ORM | SQLAlchemy 2.x | Customer/account/transaction models |
| Rules | YAML and PyYAML | AML configuration |
| Retrieval | ChromaDB | Persistent vector search |
| Embeddings | Sentence Transformers | Semantic document retrieval |
| LLM | Ollama | Local SAR generation |
| PDF | ReportLab | SAR report export |
| Testing | pytest and FastAPI TestClient | API and safety verification |

---

## Slide 17: Demonstration Dataset

### Seeded data

- Four customers.
- Four accounts.
- Ninety-four deterministic transactions.
- One suspicious customer with high-velocity pass-through activity.
- UAE outbound transfers in the suspicious window.
- Normal baseline activity for the remaining customers.

### Demonstration case

```text
Customer:          CUST_1001
Profile:           Student
Alert type:        Layering
Transactions:      28
Time window:       3 days
Destination:       UAE
Pattern:           High velocity pass-through layering
Expected outcome:  HIGH risk and SAR draft for analyst review
```

### Demo story

1. Log in as an analyst.
2. Upload `data/alert_case.json`.
3. Submit the case.
4. Inspect triggered rules and validation results.
5. Open the audit timeline.
6. Edit or approve the narrative with a comment.
7. Replay the case and inspect the diff.
8. Download the PDF report.

---

## Slide 18: Testing and Verification

### Backend tests

- Login success and invalid-password rejection.
- Authentication guard for protected endpoints.
- Case creation and risk-level response.
- Review comment validation.
- Successful case review.
- PDF content type.
- PII-safe narrative phrase enrichment.

### Safety tests

- Full-name, first-name, last-name, and mixed-case PII detection.
- Evidence-anchor coverage checks.
- Retry after PII and evidence failures.
- Maximum retry violations.
- Generation exceptions.
- Partial-evidence soft acceptance.
- Customer ID leak detection.
- Audit trail ordering and structured error output.

### Test command

```powershell
pytest -q
```

The current tests use monkeypatched in-memory persistence for API flows. A complete deployment would also add live PostgreSQL, ChromaDB, Ollama, load, and model-quality integration tests.

---

## Slide 19: Current Results

### Delivered result

The project currently demonstrates an end-to-end local workflow:

```text
 Alert -> Enrichment -> Rules -> Risk -> RAG -> LLM
       -> Validation -> Traceability -> Review -> PDF
```

### Practical value

- Reduces manual SAR drafting effort.
- Keeps AML detection deterministic and inspectable.
- Grounds generated statements in known transaction evidence.
- Separates sensitive identity data from model processing.
- Preserves intermediate artifacts for review and replay.
- Provides a usable analyst interface instead of an API-only prototype.

---

## Slide 20: Current Limitations

The following are not yet implemented in the current repository:

- Blockchain or distributed-ledger audit anchoring.
- Smart contracts or immutable external audit verification.
- Graph-based fraud detection across multiple accounts.
- Isolation Forest anomaly detection and NetworkX cycle/fan-in/fan-out analysis.
- Composite scoring that combines rule, anomaly, and graph scores.
- Production identity provider and hardened role-based authorization.
- Token expiry, refresh tokens, secret management, and password storage suitable for production.
- Automated FIU submission or core-banking integration.
- Production deployment, containers, migrations, queues, monitoring, and scaling.
- Large benchmark dataset and formal model-quality evaluation.

### Presentation wording

Use “implemented prototype” or “current milestone” when describing the repository. Do not describe the future blockchain and graph components as completed features.

---

## Slide 21: Future Enhancement Roadmap

```text
 Current milestone
       |
       v
 +-------------------------+
 | Harden authentication   |
 | and deployment          |
 +------------+------------+
              |
              v
 +-------------------------+
 | Add graph transaction   |
 | and multi-account       |
 | analysis                |
 +------------+------------+
              |
              v
 +-------------------------+
 | Add hybrid anomaly      |
 | detection model         |
 +------------+------------+
              |
              v
 +-------------------------+
 | Anchor audit hashes in  |
 | blockchain ledger       |
 +------------+------------+
              |
              v
 +-------------------------+
 | Integrate FIU and       |
 | enterprise systems      |
 +-------------------------+
```

### Priorities

1. Replace demo authentication and secrets.
2. Add live integration tests and deployment packaging.
3. Introduce graph-based relationship analysis.
4. Add Isolation Forest anomaly scoring and NetworkX graph detection.
5. Combine rule, anomaly, and graph scores into a composite risk score.
6. Add hash chaining and blockchain anchoring for audit integrity.
7. Add controlled external submission workflows.

---

## Slide 22: Conclusion

### On-slide content

The implemented system provides a complete local pipeline for explainable AML alert handling and SAR drafting:

```text
 Deterministic detection
          +
 Historical enrichment
          +
 Retrieval-augmented generation
          +
 Safety and evidence validation
          +
 Analyst-controlled review
          +
 Audit-ready export
```

### Closing statement

The current milestone establishes the SAR workflow foundation for the broader hybrid fraud detection and blockchain-audited compliance platform.

---

## Optional Appendix A: Repository Mapping

| Presentation topic | Repository location |
| --- | --- |
| API and orchestration | `backend/app.py` |
| Database and persistence | `backend/database.py` |
| Enrichment | `backend/enrichment.py` |
| Schemas | `backend/schemas.py` |
| AML rules | `rules.yaml` |
| Rule engine | `rag_pipeline/rule_engine.py` |
| RAG ingestion | `rag_pipeline/ingestion_pipeline.py` |
| RAG and generation | `rag_pipeline/pipeline_service.py` |
| Safety utilities | `sar_safety.py` |
| Frontend | `frontend/` |
| Seed and setup scripts | `scripts/` |
| Tests | `tests/` |

## Optional Appendix B: Local Run Commands

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python scripts/ensure_local_postgres.py
python scripts/seed_data.py
ollama pull mistral:7b
Push-Location rag_pipeline
python ingestion_pipeline.py
Pop-Location
uvicorn backend.app:app --reload
```

In a second terminal:

```powershell
Push-Location frontend
python -m http.server 8080
Pop-Location
```
