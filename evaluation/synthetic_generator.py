from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import Any


def generate_benchmark_dataset(
    seed: int = 42,
    base_date: datetime | None = None,
    normal_accounts_count: int = 20,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Generates a deterministic benchmark dataset of normal banking transactions
    and targeted AML suspicious laundering motifs.
    Returns: (transactions, ground_truth_labels)
    """
    rng = random.Random(seed)
    start_dt = base_date or datetime(2026, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
    
    transactions: list[dict[str, Any]] = []
    ground_truth: list[dict[str, Any]] = []
    txn_seq = 1

    def _add_txn(
        acc: str,
        cp: str,
        amt: float,
        ttype: str,
        dt: datetime,
        country: str = "IN",
        is_suspicious: bool = False,
        typology: str = "BENIGN",
    ) -> str:
        nonlocal txn_seq
        tid = f"TXN_{txn_seq:05d}"
        txn_seq += 1
        t_obj = {
            "txn_id": tid,
            "account_id": acc,
            "counterparty": cp,
            "amount": round(amt, 2),
            "txn_type": ttype,
            "country": country,
            "timestamp": dt.isoformat(),
        }
        transactions.append(t_obj)
        ground_truth.append({
            "txn_id": tid,
            "account_id": acc,
            "is_suspicious": is_suspicious,
            "typology": typology,
        })
        return tid

    # ── 1. BACKGROUND NORMAL TRAFFIC ───────────────────────────────────
    for acc_idx in range(1, normal_accounts_count + 1):
        acc_id = f"ACC_NORM_{acc_idx:03d}"
        curr_dt = start_dt + timedelta(days=rng.randint(0, 5))
        # 8-15 normal transactions over 60 days
        num_txns = rng.randint(8, 15)
        for _ in range(num_txns):
            curr_dt += timedelta(days=rng.randint(2, 5), hours=rng.randint(1, 8))
            amt = rng.uniform(500.0, 15000.0)
            ttype = "credit" if rng.random() < 0.3 else "debit"
            cp = f"MERCHANT_{rng.randint(1, 10)}" if ttype == "debit" else f"EMPLOYER_{acc_idx}"
            _add_txn(acc_id, cp, amt, ttype, curr_dt, "IN", False, "BENIGN")

    # ── 2. BENIGN CONTROLS (SUPERFICIALLY UNUSUAL BUT LEGITIMATE) ───────
    # Control 1: One-time large legitimate bonus
    c1_acc = "ACC_CTRL_BONUS"
    c1_dt = start_dt + timedelta(days=20)
    _add_txn(c1_acc, "EMPLOYER_CORP", 450000.0, "credit", c1_dt, "IN", False, "BENIGN_BONUS")
    _add_txn(c1_acc, "MUTUAL_FUND_AMFI", 300000.0, "debit", c1_dt + timedelta(days=2), "IN", False, "BENIGN_INVEST")

    # Control 2: E-commerce merchant rapid inward settlements
    c2_acc = "ACC_CTRL_MERCHANT"
    c2_dt = start_dt + timedelta(days=25)
    for i in range(12):
        _add_txn(c2_acc, f"RETAIL_CUST_{i}", rng.uniform(800, 3000), "credit", c2_dt + timedelta(hours=i * 2), "IN", False, "BENIGN_MERCHANT")

    # ── 3. SUSPICIOUS MOTIF A: STRUCTURING / SMURFING ───────────────────
    # 22 repeated transactions just below the threshold within 3 days
    s1_acc = "ACC_SUSP_STRUCT_01"
    s1_dt = start_dt + timedelta(days=35)
    for i in range(22):
        s1_dt += timedelta(hours=rng.randint(1, 3))
        # Just below reporting threshold bands
        amt = rng.uniform(48000.0, 49500.0)
        _add_txn(s1_acc, f"SMURF_BRANCH_{i % 4}", amt, "credit", s1_dt, "IN", True, "STRUCTURING")

    # ── 4. SUSPICIOUS MOTIF B: RAPID PASS-THROUGH / LAYERING ────────────
    # High inward credits followed immediately by dissipation to UAE
    s2_acc = "ACC_SUSP_PASSTHROUGH_02"
    s2_dt = start_dt + timedelta(days=40)
    _add_txn(s2_acc, "UNKNOWN_SOURCE_X", 1250000.0, "credit", s2_dt, "IN", True, "PASS_THROUGH")
    _add_txn(s2_acc, "SHELL_CORP_DUBAI", 1240000.0, "debit", s2_dt + timedelta(hours=6), "UAE", True, "PASS_THROUGH")

    # ── 5. SUSPICIOUS MOTIF C: BOUNDED CIRCULAR FLOW ───────────────────
    # Circular flow: A -> B -> C -> D -> A within 48 hours
    c_a, c_b, c_c, c_d = "ACC_LOOP_A", "ACC_LOOP_B", "ACC_LOOP_C", "ACC_LOOP_D"
    c_dt = start_dt + timedelta(days=45)
    amt_loop = 850000.0
    _add_txn(c_a, c_b, amt_loop, "debit", c_dt, "IN", True, "CIRCULAR_FLOW")
    _add_txn(c_b, c_c, amt_loop - 5000, "debit", c_dt + timedelta(hours=8), "IN", True, "CIRCULAR_FLOW")
    _add_txn(c_c, c_d, amt_loop - 10000, "debit", c_dt + timedelta(hours=16), "IN", True, "CIRCULAR_FLOW")
    _add_txn(c_d, c_a, amt_loop - 15000, "debit", c_dt + timedelta(hours=24), "IN", True, "CIRCULAR_FLOW")

    # ── 6. SUSPICIOUS MOTIF D: FAN-IN / FAN-OUT COLLECTION HUB ─────────
    hub_acc = "ACC_SUSP_MULE_HUB"
    hub_dt = start_dt + timedelta(days=50)
    for i in range(5):
        _add_txn(hub_acc, f"VICTIM_{i}", rng.uniform(40000, 90000), "credit", hub_dt + timedelta(hours=i), "IN", True, "FAN_IN_FAN_OUT")
    for j in range(5):
        _add_txn(hub_acc, f"RECIPIENT_MULE_{j}", rng.uniform(38000, 88000), "debit", hub_dt + timedelta(hours=6 + j), "IN", True, "FAN_IN_FAN_OUT")

    # Sort deterministically
    transactions.sort(key=lambda t: t["timestamp"])
    return transactions, ground_truth
