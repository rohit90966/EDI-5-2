from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from .contracts import AnalysisSnapshot


def canonical_json(obj: Any) -> str:
    """Produces deterministic canonical JSON string: sorted keys, no whitespace, standard float formatting."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def compute_sha256(data: str | bytes) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def create_analysis_snapshot(
    alert_payload: dict[str, Any],
    enrichment: dict[str, Any] | None = None,
    as_of_time: str | None = None,
) -> AnalysisSnapshot:
    """
    Builds a frozen, deterministic analysis snapshot representing all available
    knowledge at the time of analysis.
    """
    as_of = as_of_time or datetime.now(timezone.utc).isoformat()
    customer_id = str(alert_payload.get("customer_id") or "")
    enrichment = enrichment or alert_payload.get("enrichment") or {}

    raw_txns = enrichment.get("transactions") or []
    if not raw_txns and "transactions" in alert_payload:
        raw_txns = alert_payload.get("raw_transactions") or []

    # Standardize transaction objects
    canonical_txns: list[dict[str, Any]] = []
    for txn in raw_txns:
        canonical_txns.append({
            "txn_id": str(txn.get("txn_id") or txn.get("id") or ""),
            "account_id": str(txn.get("account_id") or ""),
            "amount": round(float(txn.get("amount") or 0.0), 2),
            "txn_type": str(txn.get("txn_type") or "debit").lower(),
            "country": str(txn.get("country") or "").upper(),
            "timestamp": str(txn.get("timestamp") or as_of),
            "counterparty": str(txn.get("counterparty") or "") if txn.get("counterparty") else None,
        })

    # Sort deterministically by timestamp, then txn_id
    canonical_txns.sort(key=lambda t: (t["timestamp"], t["txn_id"]))

    txn_meta = alert_payload.get("transactions") or {}
    time_window_days = int(txn_meta.get("time_window_days") or 3)

    payload_for_hashing = {
        "customer_id": customer_id,
        "as_of_time": as_of,
        "time_window_days": time_window_days,
        "customer_profile": enrichment.get("customer_profile") or {
            "customer_id": customer_id,
            "name": alert_payload.get("customer_name"),
            "occupation": alert_payload.get("customer_profile"),
        },
        "transactions": canonical_txns,
    }

    canonical_repr = canonical_json(payload_for_hashing)
    snapshot_hash = compute_sha256(canonical_repr)

    start_time = canonical_txns[0]["timestamp"] if canonical_txns else None
    end_time = canonical_txns[-1]["timestamp"] if canonical_txns else None

    return AnalysisSnapshot(
        snapshot_id=f"SNAP_{uuid4().hex[:12]}",
        as_of_time=as_of,
        customer_id=customer_id,
        time_window_days=time_window_days,
        start_time=start_time,
        end_time=end_time,
        transaction_count=len(canonical_txns),
        transactions=canonical_txns,
        customer_profile=payload_for_hashing["customer_profile"],
        snapshot_hash=snapshot_hash,
    )
