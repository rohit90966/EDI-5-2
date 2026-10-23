from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

import os

import psycopg2
from psycopg2 import sql
from psycopg2.extras import Json, RealDictCursor
from dotenv import load_dotenv
from sqlalchemy import DateTime, Float, ForeignKey, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

load_dotenv()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_database_url() -> str:
    url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/sar_audit",
    )
    # SQLAlchemy expects postgresql://, not legacy postgres:// aliases.
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


# SQLAlchemy ORM setup for enrichment domain entities.
class Base(DeclarativeBase):
    pass


class Customer(Base):
    __tablename__ = "customers"

    customer_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    occupation: Mapped[str] = mapped_column(String(255), nullable=False)
    monthly_income: Mapped[float] = mapped_column(Float, nullable=False)
    risk_rating: Mapped[str] = mapped_column(String(32), nullable=False)

    accounts: Mapped[list["Account"]] = relationship(back_populates="customer", cascade="all, delete-orphan")


class Account(Base):
    __tablename__ = "accounts"

    account_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.customer_id", ondelete="CASCADE"), nullable=False)
    account_type: Mapped[str] = mapped_column(String(64), nullable=False)
    opened_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    customer: Mapped[Customer] = relationship(back_populates="accounts")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="account", cascade="all, delete-orphan")


class Transaction(Base):
    __tablename__ = "transactions"

    txn_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.account_id", ondelete="CASCADE"), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    txn_type: Mapped[str] = mapped_column(String(16), nullable=False)
    country: Mapped[str] = mapped_column(String(64), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Optional enrichment field to support counterparty analytics.
    counterparty: Mapped[str | None] = mapped_column(String(255), nullable=True)

    account: Mapped[Account] = relationship(back_populates="transactions")


engine = create_engine(get_database_url(), future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Iterator[Any]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def get_connection() -> Iterator[Any]:
    connection = psycopg2.connect(get_database_url())
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db() -> None:
    # Ensure SQLAlchemy-managed enrichment tables exist.
    Base.metadata.create_all(bind=engine)

    ddl = """
    CREATE TABLE IF NOT EXISTS cases (
        case_id UUID PRIMARY KEY,
        alert_id TEXT NOT NULL,
        status TEXT NOT NULL,
        risk_score DOUBLE PRECISION,
        risk_level TEXT,
        alert_payload JSONB NOT NULL,
        masked_alert_payload JSONB NOT NULL,
        evidence_pack JSONB,
        retrieval_payload JSONB,
        prompt_payload JSONB,
        validation_payload JSONB,
        final_sar JSONB,
        analyst_review JSONB,
        replay_payload JSONB,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status);
    CREATE INDEX IF NOT EXISTS idx_cases_risk_score ON cases(risk_score DESC NULLS LAST);
    CREATE INDEX IF NOT EXISTS idx_cases_updated_at ON cases(updated_at DESC);

    CREATE TABLE IF NOT EXISTS audit_events (
        event_id BIGSERIAL PRIMARY KEY,
        case_id UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
        event_type TEXT NOT NULL,
        event_payload JSONB NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_audit_case_id ON audit_events(case_id, created_at);

    CREATE TABLE IF NOT EXISTS analysis_runs (
        run_id TEXT PRIMARY KEY,
        case_id UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
        alert_id TEXT NOT NULL,
        idempotency_key TEXT,
        status TEXT NOT NULL,
        snapshot_hash TEXT NOT NULL,
        composite_score DOUBLE PRECISION NOT NULL,
        risk_tier TEXT NOT NULL,
        policy_action TEXT NOT NULL,
        policy_decision JSONB NOT NULL,
        detector_results JSONB NOT NULL,
        findings JSONB NOT NULL,
        warnings JSONB,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_analysis_runs_case_id ON analysis_runs(case_id, created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_analysis_runs_idempotency ON analysis_runs(idempotency_key) WHERE idempotency_key IS NOT NULL;

    CREATE TABLE IF NOT EXISTS audit_ledger (
        sequence_number BIGINT PRIMARY KEY,
        event_uuid UUID NOT NULL UNIQUE,
        case_id UUID REFERENCES cases(case_id) ON DELETE SET NULL,
        actor_id TEXT NOT NULL,
        action_type TEXT NOT NULL,
        aggregate_type TEXT NOT NULL,
        aggregate_id TEXT,
        payload_hash TEXT NOT NULL,
        prev_hash TEXT NOT NULL,
        block_hash TEXT NOT NULL,
        schema_version TEXT NOT NULL,
        hash_version TEXT NOT NULL,
        event_payload JSONB NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_ledger_case_id ON audit_ledger(case_id, sequence_number);
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(ddl)


def create_case(case_id: str, alert_payload: dict[str, Any], masked_alert_payload: dict[str, Any]) -> None:
    query = """
    INSERT INTO cases (
        case_id,
        alert_id,
        status,
        alert_payload,
        masked_alert_payload,
        created_at,
        updated_at
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    now = utc_now()
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                query,
                (
                    case_id,
                    alert_payload["alert_id"],
                    "INGESTED",
                    Json(alert_payload),
                    Json(masked_alert_payload),
                    now,
                    now,
                ),
            )


def update_case(case_id: str, **fields: Any) -> None:
    if not fields:
        return

    assignments = []
    values = []
    fields["updated_at"] = utc_now()
    for key, value in fields.items():
        assignments.append(sql.SQL("{} = %s").format(sql.Identifier(key)))
        if isinstance(value, (dict, list)):
            values.append(Json(value))
        else:
            values.append(value)

    statement = sql.SQL("UPDATE cases SET {} WHERE case_id = %s").format(sql.SQL(", ").join(assignments))
    values.append(case_id)

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(statement, values)


def append_audit_event(case_id: str, event_type: str, event_payload: dict[str, Any]) -> None:
    query = """
    INSERT INTO audit_events (case_id, event_type, event_payload)
    VALUES (%s, %s, %s)
    """
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, (case_id, event_type, Json(event_payload)))


def get_case(case_id: str) -> dict[str, Any] | None:
    query = "SELECT * FROM cases WHERE case_id = %s"
    with get_connection() as connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, (case_id,))
            return cursor.fetchone()


def list_cases() -> list[dict[str, Any]]:
    query = """
    SELECT case_id, alert_id, status, risk_score, risk_level, final_sar, analyst_review, created_at, updated_at
    FROM cases
    ORDER BY risk_score DESC NULLS LAST, updated_at DESC
    """
    with get_connection() as connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query)
            return cursor.fetchall()


def get_audit_events(case_id: str) -> list[dict[str, Any]]:
    query = """
    SELECT event_id, case_id, event_type, event_payload, created_at
    FROM audit_events
    WHERE case_id = %s
    ORDER BY created_at, event_id
    """
    with get_connection() as connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, (case_id,))
            return cursor.fetchall()


def save_analysis_run(run_data: dict[str, Any]) -> None:
    query = """
    INSERT INTO analysis_runs (
        run_id, case_id, alert_id, idempotency_key, status, snapshot_hash,
        composite_score, risk_tier, policy_action, policy_decision,
        detector_results, findings, warnings, created_at
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (run_id) DO NOTHING
    """
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                query,
                (
                    run_data["run_id"],
                    run_data["case_id"],
                    run_data["alert_id"],
                    run_data.get("idempotency_key"),
                    run_data["status"],
                    run_data["snapshot_hash"],
                    run_data["composite_score"],
                    run_data["risk_tier"],
                    run_data["policy_action"],
                    Json(run_data["policy_decision"]),
                    Json(run_data["detector_results"]),
                    Json(run_data["findings"]),
                    Json(run_data.get("warnings") or []),
                    run_data.get("created_at") or utc_now(),
                ),
            )


def get_analysis_run(run_id: str) -> dict[str, Any] | None:
    query = "SELECT * FROM analysis_runs WHERE run_id = %s"
    with get_connection() as connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, (run_id,))
            return cursor.fetchone()


def get_latest_analysis_run(case_id: str) -> dict[str, Any] | None:
    query = """
    SELECT * FROM analysis_runs
    WHERE case_id = %s
    ORDER BY created_at DESC
    LIMIT 1
    """
    with get_connection() as connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, (case_id,))
            return cursor.fetchone()


def list_analysis_runs(case_id: str) -> list[dict[str, Any]]:
    query = """
    SELECT * FROM analysis_runs
    WHERE case_id = %s
    ORDER BY created_at DESC
    """
    with get_connection() as connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, (case_id,))
            return cursor.fetchall()


def get_audit_ledger_events(case_id: str | None = None) -> list[dict[str, Any]]:
    if case_id:
        query = """
        SELECT * FROM audit_ledger
        WHERE case_id = %s
        ORDER BY sequence_number ASC
        """
        params = (case_id,)
    else:
        query = """
        SELECT * FROM audit_ledger
        ORDER BY sequence_number ASC
        """
        params = ()

    with get_connection() as connection:
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()