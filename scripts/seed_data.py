from __future__ import annotations

import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy.exc import OperationalError

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database import Account, Customer, SessionLocal, Transaction, init_db

RANDOM = random.Random(42)
NOW_UTC = datetime.now(timezone.utc)


def _random_ts(days_back: int = 365) -> datetime:
    return NOW_UTC - timedelta(
        days=RANDOM.randint(0, days_back),
        hours=RANDOM.randint(0, 23),
        minutes=RANDOM.randint(0, 59),
    )


def _normal_txn_amount() -> float:
    return round(RANDOM.uniform(1500, 45000), 2)


def _suspicious_credit_amount() -> float:
    return round(RANDOM.uniform(35000, 85000), 2)


def seed() -> None:
    init_db()

    customers = [
        Customer(customer_id="CUST_1001", name="Arjun Malhotra", occupation="Student", monthly_income=120000.0, risk_rating="MEDIUM"),
        Customer(customer_id="CUST_1002", name="Neha Kulkarni", occupation="Software Engineer", monthly_income=175000.0, risk_rating="LOW"),
        Customer(customer_id="CUST_1003", name="Rahul Sharma", occupation="Retail Business Owner", monthly_income=95000.0, risk_rating="LOW"),
        Customer(customer_id="CUST_1004", name="Priya Menon", occupation="Freelance Designer", monthly_income=70000.0, risk_rating="LOW"),
    ]

    accounts = [
        Account(account_id="ACC_9001", customer_id="CUST_1001", account_type="current", opened_date=NOW_UTC - timedelta(days=980)),
        Account(account_id="ACC_9002", customer_id="CUST_1002", account_type="savings", opened_date=NOW_UTC - timedelta(days=820)),
        Account(account_id="ACC_9003", customer_id="CUST_1003", account_type="current", opened_date=NOW_UTC - timedelta(days=740)),
        Account(account_id="ACC_9004", customer_id="CUST_1004", account_type="savings", opened_date=NOW_UTC - timedelta(days=670)),
    ]

    counterparties_local = ["ABC Traders", "Sunrise Retail", "Metro Supplies", "BlueRock LLC", "Om Sai Services"]
    counterparties_foreign = ["Gulf Exports FZE", "Desert Link Holdings", "Al Noor Trading", "Emirates Flow LLC"]

    transactions: list[Transaction] = []

    # Normal behavior for three customers.
    txn_counter = 1
    for account_id in ["ACC_9002", "ACC_9003", "ACC_9004"]:
        for _ in range(10):
            txn_type = "credit" if RANDOM.random() < 0.55 else "debit"
            country = "India" if RANDOM.random() < 0.95 else RANDOM.choice(["Singapore", "UK"])
            transactions.append(
                Transaction(
                    txn_id=f"TXN_{txn_counter:05d}",
                    account_id=account_id,
                    amount=_normal_txn_amount(),
                    txn_type=txn_type,
                    country=country,
                    counterparty=RANDOM.choice(counterparties_local),
                    timestamp=_random_ts(360),
                )
            )
            txn_counter += 1

    # Suspicious pass-through behavior for CUST_1001 in a tight alert window.
    alert_window_start = NOW_UTC - timedelta(days=3)
    for i in range(28):
        in_ts = alert_window_start + timedelta(hours=i * 2)
        out_ts = in_ts + timedelta(minutes=35)

        in_amount = _suspicious_credit_amount()
        transactions.append(
            Transaction(
                txn_id=f"TXN_{txn_counter:05d}",
                account_id="ACC_9001",
                amount=in_amount,
                txn_type="credit",
                country="India",
                counterparty=RANDOM.choice(counterparties_local),
                timestamp=in_ts,
            )
        )
        txn_counter += 1

        transactions.append(
            Transaction(
                txn_id=f"TXN_{txn_counter:05d}",
                account_id="ACC_9001",
                amount=round(in_amount * RANDOM.uniform(0.94, 0.995), 2),
                txn_type="debit",
                country="UAE",
                counterparty=RANDOM.choice(counterparties_foreign),
                timestamp=out_ts,
            )
        )
        txn_counter += 1

    # Historical baseline activity for suspicious customer, but much lower volume.
    for _ in range(8):
        transactions.append(
            Transaction(
                txn_id=f"TXN_{txn_counter:05d}",
                account_id="ACC_9001",
                amount=round(RANDOM.uniform(8000, 18000), 2),
                txn_type="credit",
                country="India",
                counterparty=RANDOM.choice(counterparties_local),
                timestamp=_random_ts(300),
            )
        )
        txn_counter += 1

    with SessionLocal() as session:
        # Idempotent reseed.
        session.query(Transaction).delete()
        session.query(Account).delete()
        session.query(Customer).delete()

        session.add_all(customers)
        session.add_all(accounts)
        session.add_all(transactions)
        session.commit()

    print(f"Seeded {len(customers)} customers, {len(accounts)} accounts, {len(transactions)} transactions.")


if __name__ == "__main__":
    try:
        seed()
    except OperationalError as exc:
        raise SystemExit(
            "Failed to connect to PostgreSQL. Set DATABASE_URL to a valid database, "
            "for example: postgresql://postgres:postgres@localhost:5432/sar_audit"
        ) from exc
