# Member 1: Backend and API

## Role

Own the HTTP application layer and the analyst workflow. The backend member turns browser requests into validated application operations, coordinates the database and AI services, enforces authentication, and exposes stable API responses.

## Primary files

- `backend/app.py` - FastAPI app, routes, JWT authentication, orchestration, review, replay, and PDF export.
- `backend/schemas.py` - Pydantic request and response contracts.
- `tests/test_backend.py` - API and workflow tests.
- `conftest.py` - shared test setup, when a fixture change is required.

Do not put SQL query logic, rule evaluation, or prompt construction in route handlers. Call the database, enrichment, and AI abstractions instead.

## Main responsibilities

1. Maintain `GET /health` and `POST /login`.
2. Maintain protected case routes:
   - `GET /cases`
   - `POST /cases`
   - `GET /cases/{case_id}`
   - `GET /cases/{case_id}/audit`
   - `POST /cases/{case_id}/review`
   - `POST /cases/{case_id}/replay`
   - `GET /cases/{case_id}/export/pdf`
3. Validate incoming alerts with `AlertPayload` before processing.
4. Authenticate users with the existing bearer-token flow.
5. Orchestrate the sequence: validate, enrich, evaluate/generate, persist, and return a response.
6. Enforce review rules such as mandatory comments for rejection and valid case status transitions.
7. Keep PDF output readable and sanitized before ReportLab renders it.
8. Add regression tests for every new route behavior or status transition.

## Request flow to preserve

```text
Browser -> JWT auth -> Pydantic validation -> enrichment -> AI pipeline
        -> case/audit persistence -> structured API response
```

The backend must preserve raw and masked data boundaries. Raw identity data may be stored in the controlled case record, but it must not be passed to the language model.

## Example contribution

When adding a new protected endpoint, follow the existing dependency and persistence pattern:

```python
@app.get("/cases/{case_id}/audit")
def get_audit(case_id: str, current_user: dict = Depends(get_current_user)):
    case = database.get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return database.get_audit_events(case_id)
```

The exact helper names should match the existing implementation. Keep route functions thin and move reusable business behavior to the owning service.

## API contract checklist

- Return useful HTTP status codes: `401` for missing/invalid auth, `404` for unknown cases, `422` for invalid payloads, and `500` only for unexpected failures.
- Keep response fields JSON serializable and stable for `frontend/api.js`.
- Never expose passwords, signing secrets, database credentials, or internal model tokens.
- Record important lifecycle events: ingestion, processing, validation, review, replay, export, and failure.
- Do not silently swallow an AI or database error; return a clear failure and preserve the audit context.

## Testing responsibilities

Run the focused backend suite:

```powershell
pytest tests/test_backend.py -q
```

At minimum, cover login, authentication rejection, case creation, case retrieval, review validation, audit retrieval, replay, and PDF export. Test both success and failure paths.

## Handoff with other members

- **Database member:** consume database helpers and models; request new persistence methods instead of writing SQL in `app.py`.
- **AI member:** consume the pipeline service contract; provide the validated/enriched alert and persist its structured result and validation metadata.
- **Frontend member:** communicate endpoint paths, required fields, status codes, and response examples before changing a contract.

## Definition of done

- The route is authenticated when required.
- The request and response schema is documented in code.
- The happy path and the principal error paths have tests.
- A corresponding audit event exists where the action changes case state.
- Existing frontend and AI contracts still pass their tests.
