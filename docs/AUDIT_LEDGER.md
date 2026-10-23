# Cryptographic Audit Ledger & Integrity Verification

**Module:** `audit/ledger.py`, `scripts/verify_audit_ledger.py`  
**API Endpoint:** `GET /audit/ledger/verify`  
**Database Table:** `audit_ledger` (PostgreSQL)  

---

## 1. Purpose & Design Goals

To comply with global regulatory expectations regarding AML auditability (e.g., PMLA 2002 records retention, FATF Recommendation 11), all critical lifecycle events—alert ingestion, multi-detector risk scoring, RAG narrative generation, analyst review approvals/rejections, and case replays—are persisted in an **append-only, cryptographically hash-chained ledger**.

---

## 2. Canonical Block Envelope Schema

Every ledger entry contains an immutable header linked to the hash of the preceding block:

| Field | Type | Description |
|---|---|---|
| `sequence_number` | `BIGINT` | Monotonically increasing sequence number starting at 1. |
| `event_uuid` | `UUID` | Unique identifier for the ledger event. |
| `case_id` | `UUID` | Foreign key referencing the associated case. |
| `actor_id` | `TEXT` | Identity of the user or system subsystem executing the action. |
| `action_type` | `TEXT` | Action classification (e.g. `DETECTION_RUN_COMPLETED`, `ANALYST_REVIEW_SUBMITTED`). |
| `aggregate_type` | `TEXT` | Root aggregate (`CASE`, `ANALYSIS_RUN`, `SYSTEM`). |
| `aggregate_id` | `TEXT` | Identifier of the specific aggregate. |
| `payload_hash` | `TEXT (HEX)` | $\text{SHA-256}(\text{canonical\_json}(\text{event\_payload}))$. |
| `prev_hash` | `TEXT (HEX)` | The `block_hash` of the immediately preceding block (`"0" * 64` for genesis). |
| `block_hash` | `TEXT (HEX)` | $\text{SHA-256}(\text{canonical\_json}(\text{header\_with\_prev\_hash}))$. |
| `schema_version` | `TEXT` | `1.0.0` |
| `hash_version` | `TEXT` | `sha256-v1` |
| `created_at` | `TIMESTAMPTZ` | Normalized UTC ISO-8601 timestamp. |
| `event_payload` | `JSONB` | Non-PII structured payload describing the event facts. |

---

## 3. Cryptographic Hashing Algorithms

### 3.1 Canonical JSON Serialization
To guarantee cross-platform deterministic byte generation:
- Object dictionary keys are strictly sorted in lexicographical order.
- Separators are stripped of whitespace: `(",", ":")`.
- Timestamps are normalized to UTC ISO-8601 strings.
- Floats are rounded to deterministic decimal precision.

### 3.2 Hashing Formulas
1. **Payload Hash:**
   $$\text{payload\_hash} = \text{SHA-256}(\text{canonical\_json}(\text{event\_payload}))$$
2. **Block Header Hash:**
   $$\text{block\_hash} = \text{SHA-256}(\text{canonical\_json}(\{ \text{seq}, \text{uuid}, \text{action}, \text{actor}, \text{timestamp}, \text{agg\_type}, \text{agg\_id}, \text{payload\_hash}, \text{prev\_hash}, \text{schema\_ver}, \text{hash\_ver} \}))$$

---

## 4. Verification Engine & Invariant Checks

The read-only verifier `verify_ledger()` sequentially walks the chain from block 1 through $N$, verifying:
1. **Monotonic Sequence Continuity:** Confirms $s_{i} = s_{i-1} + 1$ with zero gaps or duplicate indices.
2. **Payload Hash Integrity:** Recalculates $\text{SHA-256}(\text{payload})$ and verifies equality with `payload_hash`.
3. **Cryptographic Linkage:** Asserts that $\text{prev\_hash}_i = \text{block\_hash}_{i-1}$.
4. **Block Hash Recomputation:** Recalculates the full header hash and verifies equality with stored `block_hash`.

If any violation occurs, the verifier terminates and emits a structured failure report with the exact sequence number and mismatch category (`PAYLOAD_TAMPER`, `LINK_TAMPER`, `HASH_TAMPER`, or `SEQUENCE_GAP`).

---

## 5. Tamper Detection Demonstration

A deterministic automated demonstration script proves tamper evidence in an isolated test environment:

```bash
.venv\Scripts\python.exe scripts/verify_audit_ledger.py --demo
```

### Demonstration Steps:
1. Appends 4 valid lifecycle events to the ledger.
2. Verifies the intact chain ($\to \text{valid} = \text{True}$).
3. Simulates an unauthorized adversarial edit in the database (altering Block 2 `risk_score` from `0.88` to `0.10`).
4. Executes `verify_ledger()`.
5. Confirms that verification fails immediately at Block 2 with status `PAYLOAD_TAMPER`.

---

## 6. Honest Threat Model & Trust Boundary Disclaimer

> [!IMPORTANT]
> **Enterprise Trust Boundary Statement**  
> While the hash chain prevents silent tampering, retro-editing, and row deletions from application-level users or SQL injection, it operates within the local PostgreSQL database engine. A database administrator with full root privileges could theoretically alter historical rows and recompute the hash chain.  
> *Production Recommendation:* Anchor daily block hashes to an external, write-once-read-many (WORM) storage system or public/consortium ledger checkpoint to achieve external trust independence. In this academic/hackathon prototype, external checkpoints are documented as `DISABLED (Local DB Hash Chain Only)`.
