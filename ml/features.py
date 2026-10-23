from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np

FEATURE_SCHEMA_VERSION = "2026.1"
FEATURE_NAMES = [
    "amount",
    "amount_to_median_ratio",
    "amount_mad_zscore",
    "rolling_count_24h",
    "rolling_amount_24h",
    "rolling_count_7d",
    "rolling_amount_7d",
    "rolling_count_30d",
    "rolling_amount_30d",
    "unique_counterparties_30d",
    "new_counterparties_ratio_30d",
    "velocity_txns_per_day",
    "hour_sin",
    "hour_cos",
    "day_of_week",
    "inflow_outflow_ratio",
]


def _parse_iso(ts: str | datetime) -> datetime:
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            return ts.replace(tzinfo=timezone.utc)
        return ts.astimezone(timezone.utc)
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return datetime.now(timezone.utc)


def extract_transaction_features(
    target_txn: dict[str, Any],
    historical_txns: list[dict[str, Any]],
    as_of_time: str | datetime | None = None,
) -> tuple[np.ndarray, dict[str, float]]:
    """
    Extracts a deterministic feature vector for a specific transaction against
    its preceding transaction history up to as_of_time.
    No future leakage is allowed.
    """
    as_of_dt = _parse_iso(as_of_time) if as_of_time else _parse_iso(target_txn.get("timestamp", datetime.now(timezone.utc)))
    target_ts = _parse_iso(target_txn.get("timestamp", as_of_dt))
    target_amount = float(target_txn.get("amount") or 0.0)

    # Filter strictly to transactions occurring strictly BEFORE target transaction
    # to guarantee target transaction cannot improperly influence its own historical baseline
    strictly_prior = [
        t for t in historical_txns
        if _parse_iso(t.get("timestamp", as_of_dt)) < target_ts
    ]

    if strictly_prior:
        prior_amounts = [float(t.get("amount") or 0.0) for t in strictly_prior]
        median_amount = float(np.median(prior_amounts))
        mad = float(np.median(np.abs(np.array(prior_amounts) - median_amount)))
        if mad == 0.0:
            mad = 1.0
    else:
        # Explicit cohort baseline fallback for cold-start initial transaction
        median_amount = 5000.0
        mad = 2000.0

    amount_to_median_ratio = target_amount / (median_amount + 1e-4)
    amount_mad_zscore = (target_amount - median_amount) / (1.4826 * mad + 1e-4)

    # Time-window subsets
    window_24h = target_ts - timedelta(hours=24)
    window_7d = target_ts - timedelta(days=7)
    window_30d = target_ts - timedelta(days=30)

    txns_24h = [t for t in strictly_prior if _parse_iso(t.get("timestamp", as_of_dt)) >= window_24h]
    txns_7d = [t for t in strictly_prior if _parse_iso(t.get("timestamp", as_of_dt)) >= window_7d]
    txns_30d = [t for t in strictly_prior if _parse_iso(t.get("timestamp", as_of_dt)) >= window_30d]

    rolling_count_24h = float(len(txns_24h))
    rolling_amount_24h = float(sum(float(t.get("amount") or 0.0) for t in txns_24h))
    rolling_count_7d = float(len(txns_7d))
    rolling_amount_7d = float(sum(float(t.get("amount") or 0.0) for t in txns_7d))
    rolling_count_30d = float(len(txns_30d))
    rolling_amount_30d = float(sum(float(t.get("amount") or 0.0) for t in txns_30d))

    # Counterparty dynamics
    cps_30d = [str(t.get("counterparty")) for t in txns_30d if t.get("counterparty")]
    unique_cps_30d = float(len(set(cps_30d)))

    # History older than 30d
    prior_txns = [t for t in strictly_prior if _parse_iso(t.get("timestamp", as_of_dt)) < window_30d]
    prior_cps = {str(t.get("counterparty")) for t in prior_txns if t.get("counterparty")}
    new_cps_count = sum(1 for cp in set(cps_30d) if cp not in prior_cps)
    new_cps_ratio = (new_cps_count / unique_cps_30d) if unique_cps_30d > 0 else 0.0

    velocity_txns_per_day = rolling_count_7d / 7.0

    # Temporal cyclic features
    hour = target_ts.hour + target_ts.minute / 60.0
    hour_sin = math.sin(2 * math.pi * hour / 24.0)
    hour_cos = math.cos(2 * math.pi * hour / 24.0)
    day_of_week = float(target_ts.weekday())

    # Inflow vs outflow
    credits_30d = sum(float(t.get("amount") or 0.0) for t in txns_30d if str(t.get("txn_type", "")).lower() == "credit")
    debits_30d = sum(float(t.get("amount") or 0.0) for t in txns_30d if str(t.get("txn_type", "")).lower() == "debit")
    inflow_outflow_ratio = (credits_30d / (debits_30d + 1e-4)) if debits_30d > 0 else 1.0

    features_dict = {
        "amount": target_amount,
        "amount_to_median_ratio": round(amount_to_median_ratio, 4),
        "amount_mad_zscore": round(amount_mad_zscore, 4),
        "rolling_count_24h": rolling_count_24h,
        "rolling_amount_24h": round(rolling_amount_24h, 2),
        "rolling_count_7d": rolling_count_7d,
        "rolling_amount_7d": round(rolling_amount_7d, 2),
        "rolling_count_30d": rolling_count_30d,
        "rolling_amount_30d": round(rolling_amount_30d, 2),
        "unique_counterparties_30d": unique_cps_30d,
        "new_counterparties_ratio_30d": round(new_cps_ratio, 4),
        "velocity_txns_per_day": round(velocity_txns_per_day, 4),
        "hour_sin": round(hour_sin, 4),
        "hour_cos": round(hour_cos, 4),
        "day_of_week": day_of_week,
        "inflow_outflow_ratio": round(inflow_outflow_ratio, 4),
    }

    vec = np.array([features_dict[name] for name in FEATURE_NAMES], dtype=np.float64)
    return vec, features_dict


def build_dataset_feature_matrix(
    transactions: list[dict[str, Any]],
    as_of_time: str | datetime | None = None,
) -> tuple[np.ndarray, list[dict[str, float]], list[str]]:
    """
    Builds a full 2D feature matrix for a sequence of transactions.
    Returns (matrix, list_of_dicts, txn_ids).
    """
    matrix: list[np.ndarray] = []
    dict_list: list[dict[str, float]] = []
    txn_ids: list[str] = []

    sorted_txns = sorted(transactions, key=lambda t: str(t.get("timestamp", "")))

    for idx, txn in enumerate(sorted_txns):
        # Pass preceding up to current
        history = sorted_txns[:idx + 1]
        vec, feat_dict = extract_transaction_features(txn, history, as_of_time=as_of_time)
        matrix.append(vec)
        dict_list.append(feat_dict)
        txn_ids.append(str(txn.get("txn_id") or f"TXN_{idx}"))

    if not matrix:
        return np.empty((0, len(FEATURE_NAMES)), dtype=np.float64), [], []

    return np.vstack(matrix), dict_list, txn_ids
