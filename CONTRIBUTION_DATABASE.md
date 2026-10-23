# Member 4: Database, Enrichment, and Seed Data

## Role

Own reliable persistence and the historical data intelligence used by the AML pipeline. This member manages PostgreSQL models, SQLAlchemy access, customer/account/transaction enrichment, case and audit storage, local setup, and realistic seed data.

## Primary files

- `backend/database.py` - SQLAlchemy models, database initialization, case persistence, and audit persistence.
- `backend/enrichment.py` - customer lookup, account relationships, transaction windows, and derived metrics.
- `scripts/ensure_local_postgres.py` - local database setup support.
- `scripts/seed_data.py` - reproducible customers, accounts, and transactions.
- `data/alert_case.json` - sample alert compatible with the seeded data.
- `tests/` - persistence and enrichment tests added for changed behavior.

## Main responsibilities

1. Keep the customer, account, transaction, case, and audit-event models consistent with application contracts.
2. Initialize tables safely through the existing startup path.
3. Provide database helpers for create, read, update, and audit operations without leaking sessions or connections.
4. Enrich alerts using the customer ID and linked accounts.
5. Calculate the twelve-month history, alert-window transactions, historical average inflow, deviation, destination country, and counterparty relationships.
6. Keep unknown-customer and no-account fallback behavior explicit and safe.
7. Keep seed data reproducible and aligned with `data/alert_case.json`.
8. Avoid storing secrets in source files or seed records.

## Data model ownership

| Entity | Purpose |
| --- | --- |
| `customers` | KYC profile, occupation, income, and risk rating |
| `accounts` | Customer-account relationship and account metadata |
| `transactions` | Amount, type, country, timestamp, and counterparty evidence |
| `cases` | Original/masked alert, risk result, AI artifacts, review state, and timestamps |
| `audit_events` | Ordered, case-linked lifecycle events and JSON payloads |

Foreign-key relationships and timestamp semantics matter. Transaction analysis depends on consistent timezone handling and on a stable customer-to-account-to-transaction relationship.

## Enrichment contract

For a known customer, return enough data for rules and evidence mapping, including:

- Customer profile and risk information.
- Linked accounts.
- Twelve-month transactions.
- Alert-window transactions.
- Alert-window transaction count and credit inflow.
- Twelve-month average monthly credit deposits.
- Percentage deviation from historical inflow.
- Dominant debit destination country.
- Unique, prior, and new counterparties.
- Whether the customer has a prior counterparty relationship.

For an unknown customer, return a minimal fallback object with empty history and zero-valued derived metrics where appropriate. Do not fabricate transaction evidence.

## Example enrichment pattern

Keep calculations in `backend/enrichment.py`, not in route handlers:

```python
history = get_transactions_for_accounts(session, account_ids, start, end)
alert_transactions = select_alert_window(history, alert_window_start)

return {
    "historical_transactions": serialize_transactions(history),
    "alert_window_transactions": serialize_transactions(alert_transactions),
    "alert_window_inflow": sum_credit_amount(alert_transactions),
    "new_counterparties_count": count_new_counterparties(history, alert_transactions),
}
```

Use the existing project helpers and models; the snippet describes ownership, not a replacement API.

## Database quality checklist

- Use parameterized SQLAlchemy queries; do not build SQL from user input.
- Close sessions through the existing dependency/context pattern.
- Preserve decimal and timestamp precision appropriate for financial data.
- Add indexes for fields used repeatedly in lookups, especially customer, account, transaction, and case identifiers.
- Keep audit events append-only from the application perspective.
- Make seed scripts safe to rerun or document the reset requirement clearly.
- Keep migrations or schema changes documented in the pull request and reflected in tests.

## Local verification

Start the local PostgreSQL setup used by the repository, seed data, and then run tests:

```powershell
python scripts/ensure_local_postgres.py
python scripts/seed_data.py
pytest -q
```

Verify that `CUST_1001` and the sample alert produce historical enrichment and suspicious transaction evidence. Also test an unknown customer, a customer with no account, an empty transaction history, and a customer with no alert-window transactions.

## Handoff with other members

- **Backend member:** expose persistence helpers and stable return shapes; do not require the API layer to know table internals.
- **AI member:** document every derived enrichment field and its units, date window, and null/empty behavior.
- **Frontend member:** frontend must receive database data through API responses, never through direct database access.

## Definition of done

- Models and relationships initialize correctly.
- Normal and fallback enrichment paths are tested.
- Seed data remains compatible with the sample alert and rule thresholds.
- Case and audit writes are durable and ordered.
- No credentials or personal data beyond intentional local demo fixtures are committed.
