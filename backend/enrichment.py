from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from .database import Account, Customer, SessionLocal, Transaction


def _to_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _month_key(value: datetime) -> str:
    return value.strftime("%Y-%m")


def _safe_dt(value: datetime | None, fallback: datetime) -> datetime:
    if value is None:
        return fallback
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def enrich_case(alert_json: dict[str, Any]) -> dict[str, Any]:
    """Enrich an incoming alert with KYC + 12-month transaction intelligence."""
    with SessionLocal() as session:
        return _enrich_case_with_session(alert_json, session)


def _enrich_case_with_session(alert_json: dict[str, Any], session: Session) -> dict[str, Any]:
    customer_id = str(alert_json.get("customer_id", "")).strip()
    now_utc = datetime.now(timezone.utc)

    customer = session.get(Customer, customer_id) if customer_id else None
    if customer is None:
        # Return a minimal enrichment object so pipeline remains functional.
        return {
            "customer_profile": {
                "customer_id": customer_id,
                "name": str(alert_json.get("customer_name", "")),
                "occupation": str(alert_json.get("customer_profile", "UNKNOWN")),
                "monthly_income": None,
                "risk_rating": "UNKNOWN",
            },
            "historical_avg": 0.0,
            "deviation_percent": None,
            "num_counterparties": 0,
            "unique_counterparties_count": 0,
            "prior_counterparties_count": 0,
            "new_counterparties_count": 0,
            "has_prior_relationship": False,
            "date_range": [None, None],
            "transactions": [],
            "alert_window_transactions": [],
            "no_prior_relationship_found": False,
            "no_prior_relationship_count": 0,
            "alert_window_transaction_count": 0,
            "alert_window_total_inflow": 0.0,
            "dominant_destination_country": str(alert_json.get("transactions", {}).get("destination_country") or "UNKNOWN"),
        }

    accounts = session.query(Account).filter(Account.customer_id == customer.customer_id).all()
    account_ids = [a.account_id for a in accounts]

    if not account_ids:
        return {
            "customer_profile": {
                "customer_id": customer.customer_id,
                "name": customer.name,
                "occupation": customer.occupation,
                "monthly_income": customer.monthly_income,
                "risk_rating": customer.risk_rating,
            },
            "historical_avg": 0.0,
            "deviation_percent": None,
            "num_counterparties": 0,
            "unique_counterparties_count": 0,
            "prior_counterparties_count": 0,
            "new_counterparties_count": 0,
            "has_prior_relationship": False,
            "date_range": [None, None],
            "transactions": [],
            "alert_window_transactions": [],
            "no_prior_relationship_found": False,
            "no_prior_relationship_count": 0,
            "alert_window_transaction_count": 0,
            "alert_window_total_inflow": 0.0,
            "dominant_destination_country": str(alert_json.get("transactions", {}).get("destination_country") or "UNKNOWN"),
        }

    latest_txn = (
        session.query(Transaction)
        .filter(Transaction.account_id.in_(account_ids))
        .order_by(Transaction.timestamp.desc())
        .first()
    )
    reference_end = _safe_dt(latest_txn.timestamp if latest_txn else None, now_utc)
    lookback_start = reference_end - timedelta(days=365)

    all_12m = (
        session.query(Transaction)
        .filter(Transaction.account_id.in_(account_ids), Transaction.timestamp >= lookback_start)
        .order_by(Transaction.timestamp.asc())
        .all()
    )

    alert_window_days = int(alert_json.get("transactions", {}).get("time_window_days") or 3)
    alert_start = reference_end - timedelta(days=alert_window_days)
    alert_window_txns = [
        t for t in all_12m
        if _safe_dt(t.timestamp, reference_end) >= alert_start and _safe_dt(t.timestamp, reference_end) <= reference_end
    ]

    deposits_12m = [t for t in all_12m if str(t.txn_type).lower() == "credit"]
    monthly_deposits: dict[str, float] = defaultdict(float)
    for txn in deposits_12m:
        monthly_deposits[_month_key(_safe_dt(txn.timestamp, reference_end))] += float(txn.amount)

    historical_avg = round(sum(monthly_deposits.values()) / 12.0, 2) if monthly_deposits else 0.0
    total_inflow_alert_window = round(
        sum(float(t.amount) for t in alert_window_txns if str(t.txn_type).lower() == "credit"),
        2,
    )

    deviation_percent: float | None = None
    if historical_avg > 0:
        deviation_percent = round(((total_inflow_alert_window - historical_avg) / historical_avg) * 100, 1)

    counterparties = {
        (t.counterparty or "").strip()
        for t in alert_window_txns
        if (t.counterparty or "").strip()
    }
    num_counterparties = len(counterparties)

    prior_counterparties = {
        (t.counterparty or "").strip()
        for t in all_12m
        if _safe_dt(t.timestamp, reference_end) < alert_start and (t.counterparty or "").strip()
    }
    new_counterparties = counterparties - prior_counterparties

    debit_countries = [t.country for t in alert_window_txns if str(t.txn_type).lower() == "debit" and t.country]
    dominant_country = Counter(debit_countries).most_common(1)[0][0] if debit_countries else (
        str(alert_json.get("transactions", {}).get("destination_country") or "UNKNOWN")
    )

    txns_payload = [
        {
            "txn_id": t.txn_id,
            "account_id": t.account_id,
            "amount": float(t.amount),
            "txn_type": t.txn_type,
            "country": t.country,
            "counterparty": t.counterparty,
            "timestamp": _to_iso(_safe_dt(t.timestamp, reference_end)),
        }
        for t in alert_window_txns
    ]

    all_txns_payload = [
        {
            "txn_id": t.txn_id,
            "account_id": t.account_id,
            "amount": float(t.amount),
            "txn_type": t.txn_type,
            "country": t.country,
            "counterparty": t.counterparty,
            "timestamp": _to_iso(_safe_dt(t.timestamp, reference_end)),
        }
        for t in all_12m
    ]

    range_start = min((_safe_dt(t.timestamp, reference_end) for t in alert_window_txns), default=alert_start)
    range_end = max((_safe_dt(t.timestamp, reference_end) for t in alert_window_txns), default=reference_end)

    return {
        "customer_profile": {
            "customer_id": customer.customer_id,
            "name": customer.name,
            "occupation": customer.occupation,
            "monthly_income": float(customer.monthly_income),
            "risk_rating": customer.risk_rating,
        },
        "historical_avg": historical_avg,
        "deviation_percent": deviation_percent,
        "num_counterparties": num_counterparties,
        "unique_counterparties_count": num_counterparties,
        "prior_counterparties_count": len(prior_counterparties),
        "new_counterparties_count": len(new_counterparties),
        "has_prior_relationship": len(prior_counterparties) > 0,
        "date_range": [_to_iso(range_start), _to_iso(range_end)],
        # Keep legacy key but upgrade to full 12-month list for stronger traceability.
        "transactions": all_txns_payload,
        "alert_window_transactions": txns_payload,
        "no_prior_relationship_found": len(new_counterparties) > 0,
        "no_prior_relationship_count": len(new_counterparties),
        "alert_window_transaction_count": len(alert_window_txns),
        "alert_window_total_inflow": total_inflow_alert_window,
        "dominant_destination_country": dominant_country,
    }
