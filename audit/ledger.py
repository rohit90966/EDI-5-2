from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

GENESIS_PREV_HASH = "0" * 64
HASH_VERSION = "sha256-v1"
SCHEMA_VERSION = "1.0.0"

_ledger_lock = threading.Lock()
# In-memory ledger store for test environments or when DB is bypassed
_in_memory_ledger: list[dict[str, Any]] = []


def canonical_serialize(obj: Any) -> str:
    """Deterministic JSON serializer: sorted keys, no whitespace, standard string conversions."""
    def _default(val: Any) -> Any:
        if isinstance(val, (datetime,)):
            if val.tzinfo is None:
                val = val.replace(tzinfo=timezone.utc)
            return val.astimezone(timezone.utc).isoformat()
        if hasattr(val, "isoformat"):
            return val.isoformat()
        return str(val)

    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=_default)


def compute_payload_hash(payload: Any) -> str:
    serialized = canonical_serialize(payload)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def compute_block_hash(
    sequence_number: int,
    event_uuid: str,
    action_type: str,
    actor_id: str,
    timestamp: str,
    aggregate_type: str,
    aggregate_id: str | None,
    payload_hash: str,
    prev_hash: str,
    schema_version: str = SCHEMA_VERSION,
    hash_version: str = HASH_VERSION,
) -> str:
    header = {
        "sequence_number": sequence_number,
        "event_uuid": event_uuid,
        "action_type": action_type,
        "actor_id": actor_id,
        "timestamp": timestamp,
        "aggregate_type": aggregate_type,
        "aggregate_id": aggregate_id or "",
        "payload_hash": payload_hash,
        "prev_hash": prev_hash,
        "schema_version": schema_version,
        "hash_version": hash_version,
    }
    serialized = canonical_serialize(header)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class LedgerVerificationResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    is_valid: bool
    verified_count: int
    first_failing_sequence: int | None = None
    mismatch_category: str | None = None  # SEQUENCE_GAP, PAYLOAD_TAMPER, LINK_TAMPER, HASH_TAMPER
    details: str = "Ledger integrity intact"
    external_checkpoint_status: str = "DISABLED (Local DB Hash Chain Only - Single Node Demo)"
    verified_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def append_ledger_block(
    case_id: str | None,
    action_type: str,
    payload: dict[str, Any],
    actor_id: str = "system",
    aggregate_type: str = "CASE",
    aggregate_id: str | None = None,
    connection: Any = None,
) -> dict[str, Any]:
    """
    Appends a new cryptographically hash-chained event to the ledger.
    Thread-safe and concurrency-guarded.
    """
    with _ledger_lock:
        now_utc = datetime.now(timezone.utc).isoformat()
        event_uuid = str(uuid4())
        payload_hash = compute_payload_hash(payload)

        # 1. Determine prior block hash and sequence number
        prev_hash = GENESIS_PREV_HASH
        sequence_number = 1

        if connection is not None:
            try:
                with connection.cursor() as cursor:
                    # Select latest block under table lock or last row
                    cursor.execute("""
                        SELECT sequence_number, block_hash
                        FROM audit_ledger
                        ORDER BY sequence_number DESC
                        LIMIT 1
                        FOR UPDATE
                    """)
                    row = cursor.fetchone()
                    if row:
                        sequence_number = row[0] + 1
                        prev_hash = row[1]
            except Exception:
                # Fallback to in-memory if table does not exist or query fails
                if _in_memory_ledger:
                    sequence_number = _in_memory_ledger[-1]["sequence_number"] + 1
                    prev_hash = _in_memory_ledger[-1]["block_hash"]
        else:
            if _in_memory_ledger:
                sequence_number = _in_memory_ledger[-1]["sequence_number"] + 1
                prev_hash = _in_memory_ledger[-1]["block_hash"]

        block_hash = compute_block_hash(
            sequence_number=sequence_number,
            event_uuid=event_uuid,
            action_type=action_type,
            actor_id=actor_id,
            timestamp=now_utc,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id or case_id,
            payload_hash=payload_hash,
            prev_hash=prev_hash,
        )

        entry = {
            "sequence_number": sequence_number,
            "event_uuid": event_uuid,
            "case_id": case_id,
            "actor_id": actor_id,
            "action_type": action_type,
            "aggregate_type": aggregate_type,
            "aggregate_id": aggregate_id or case_id,
            "payload_hash": payload_hash,
            "prev_hash": prev_hash,
            "block_hash": block_hash,
            "schema_version": SCHEMA_VERSION,
            "hash_version": HASH_VERSION,
            "event_payload": payload,
            "created_at": now_utc,
        }

        # Persist to database if connection provided
        if connection is not None:
            try:
                from psycopg2.extras import Json
                with connection.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO audit_ledger (
                            sequence_number, event_uuid, case_id, actor_id, action_type,
                            aggregate_type, aggregate_id, payload_hash, prev_hash,
                            block_hash, schema_version, hash_version, event_payload, created_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        sequence_number, event_uuid, case_id, actor_id, action_type,
                        aggregate_type, aggregate_id or case_id, payload_hash, prev_hash,
                        block_hash, SCHEMA_VERSION, HASH_VERSION, Json(payload), now_utc
                    ))
            except Exception:
                pass  # Keep in-memory copy

        _in_memory_ledger.append(entry)
        return entry


def verify_ledger(events: list[dict[str, Any]] | None = None) -> LedgerVerificationResult:
    """
    Read-only validation of the audit ledger hash chain.
    Validates:
      1. Monotonic sequence numbering with no gaps or duplicates.
      2. Deterministic payload hashing.
      3. Cryptographic link from each block to its predecessor.
      4. Exact block hash recalculation.
    """
    chain = events if events is not None else list(_in_memory_ledger)

    if not chain:
        return LedgerVerificationResult(
            is_valid=True,
            verified_count=0,
            details="Ledger is empty; genesis valid.",
        )

    # Sort by sequence number
    sorted_chain = sorted(chain, key=lambda e: int(e.get("sequence_number", 0)))
    expected_prev = GENESIS_PREV_HASH

    for idx, block in enumerate(sorted_chain):
        seq = int(block.get("sequence_number", 0))
        expected_seq = idx + 1

        # Check sequence continuity
        if seq != expected_seq:
            return LedgerVerificationResult(
                is_valid=False,
                verified_count=idx,
                first_failing_sequence=seq,
                mismatch_category="SEQUENCE_GAP",
                details=f"Sequence discontinuity at index {idx}: expected {expected_seq}, found {seq}.",
            )

        # Check payload hash integrity
        stored_payload_hash = block.get("payload_hash", "")
        recalculated_payload_hash = compute_payload_hash(block.get("event_payload", {}))
        if stored_payload_hash != recalculated_payload_hash:
            return LedgerVerificationResult(
                is_valid=False,
                verified_count=idx,
                first_failing_sequence=seq,
                mismatch_category="PAYLOAD_TAMPER",
                details=(
                    f"Payload tampering detected at sequence {seq}. "
                    f"Stored: {stored_payload_hash}, Recalculated: {recalculated_payload_hash}."
                ),
            )

        # Check previous block hash linkage
        stored_prev = block.get("prev_hash", "")
        if stored_prev != expected_prev:
            return LedgerVerificationResult(
                is_valid=False,
                verified_count=idx,
                first_failing_sequence=seq,
                mismatch_category="LINK_TAMPER",
                details=(
                    f"Broken hash chain link at sequence {seq}. "
                    f"Expected previous block hash: {expected_prev}, Found: {stored_prev}."
                ),
            )

        # Check current block hash calculation
        stored_block_hash = block.get("block_hash", "")
        recalculated_block_hash = compute_block_hash(
            sequence_number=seq,
            event_uuid=str(block.get("event_uuid", "")),
            action_type=str(block.get("action_type", "")),
            actor_id=str(block.get("actor_id", "system")),
            timestamp=str(block.get("created_at") or block.get("timestamp", "")),
            aggregate_type=str(block.get("aggregate_type", "CASE")),
            aggregate_id=str(block.get("aggregate_id") or block.get("case_id", "")),
            payload_hash=stored_payload_hash,
            prev_hash=stored_prev,
            schema_version=str(block.get("schema_version", SCHEMA_VERSION)),
            hash_version=str(block.get("hash_version", HASH_VERSION)),
        )

        if stored_block_hash != recalculated_block_hash:
            return LedgerVerificationResult(
                is_valid=False,
                verified_count=idx,
                first_failing_sequence=seq,
                mismatch_category="HASH_TAMPER",
                details=(
                    f"Block hash mutation at sequence {seq}. "
                    f"Stored: {stored_block_hash}, Recalculated: {recalculated_block_hash}."
                ),
            )

        expected_prev = stored_block_hash

    return LedgerVerificationResult(
        is_valid=True,
        verified_count=len(sorted_chain),
        details=f"All {len(sorted_chain)} blocks successfully verified. Hash chain is unbroken.",
    )


def reset_in_memory_ledger() -> None:
    """Helper for unit and integration testing."""
    with _ledger_lock:
        _in_memory_ledger.clear()
