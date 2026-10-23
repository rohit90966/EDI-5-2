from __future__ import annotations

from typing import Any
from detection.contracts import TransactionEvidence
from data_generator.models import AccountRecord, CustomerProfile, TransactionRecord


def transaction_record_to_evidence(txn: TransactionRecord | dict[str, Any]) -> TransactionEvidence:
    """Converts a synthetic transaction record into the existing detection pipeline's TransactionEvidence."""
    if isinstance(txn, dict):
        tid = str(txn.get("txn_id") or "")
        amt = float(txn.get("amount") or 0.0)
        ts = str(txn.get("timestamp") or "")
        ttype = str(txn.get("txn_type") or "debit")
        acc = str(txn.get("account_id") or "")
        cp = str(txn.get("counterparty") or "")
        cntry = str(txn.get("country") or "IN")
    else:
        tid = txn.txn_id
        amt = txn.amount
        ts = txn.timestamp
        ttype = txn.txn_type
        acc = txn.account_id
        cp = txn.counterparty
        cntry = txn.country

    return TransactionEvidence(
        txn_id=tid,
        amount=amt,
        timestamp=ts,
        txn_type=ttype,
        source_account=acc if ttype == "debit" else cp,
        destination_account=cp if ttype == "debit" else acc,
        country=cntry,
        counterparty=cp,
        metadata={"purpose": "synthetic_benchmark"},
    )


def build_alert_payload_for_case(
    account: AccountRecord | dict[str, Any],
    customer: CustomerProfile | dict[str, Any],
    case_transactions: list[TransactionRecord | dict[str, Any]],
    historical_transactions: list[TransactionRecord | dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Builds the exact alert payload required by RulesEngineDetector and MultiDetectorService,
    maintaining complete backward compatibility with the existing SAR pipeline.
    """
    acc_id = account.account_id if isinstance(account, AccountRecord) else str(account.get("account_id"))
    cust_occ = customer.occupation if isinstance(customer, CustomerProfile) else str(customer.get("occupation"))
    monthly_inc = customer.monthly_income if isinstance(customer, CustomerProfile) else float(customer.get("monthly_income") or 0.0)

    txns_raw = [
        t if isinstance(t, dict) else {
            "txn_id": t.txn_id,
            "account_id": t.account_id,
            "counterparty": t.counterparty,
            "amount": t.amount,
            "txn_type": t.txn_type,
            "country": t.country,
            "timestamp": t.timestamp,
        }
        for t in case_transactions
    ]

    hist_raw = [
        t if isinstance(t, dict) else {
            "txn_id": t.txn_id,
            "account_id": t.account_id,
            "counterparty": t.counterparty,
            "amount": t.amount,
            "txn_type": t.txn_type,
            "country": t.country,
            "timestamp": t.timestamp,
        }
        for t in (historical_transactions or [])
    ]

    return {
        "alert_id": f"ALERT_{acc_id}",
        "account_id": acc_id,
        "customer_occupation": cust_occ,
        "monthly_income": monthly_inc,
        "raw_transactions": txns_raw,
        "enrichment": {
            "customer_profile": {
                "occupation": cust_occ,
                "monthly_income": monthly_inc,
            },
            "transactions": hist_raw,
        },
    }
