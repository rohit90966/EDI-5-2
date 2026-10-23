# Member 2: Frontend and Analyst Experience

## Role

Own the browser-based analyst experience. The frontend member makes the complete workflow usable: login, alert upload, case monitoring, narrative review, audit inspection, and PDF download.

## Primary files

- `frontend/index.html` - login screen and token acquisition.
- `frontend/new_case.html` - alert JSON upload, validation preview, and submission.
- `frontend/dashboard.html` - case list, risk summaries, and navigation.
- `frontend/review.html` - narrative, validation result, edit, approve, reject, and replay controls.
- `frontend/audit.html` - chronological audit timeline.
- `frontend/api.js` - authenticated HTTP client and shared API helpers.
- `frontend/style.css` - shared layout, states, responsive behavior, and visual styling.

## Main responsibilities

1. Keep login and `sessionStorage` token handling reliable.
2. Make alert upload understandable before submission and show backend validation errors clearly.
3. Render risk level, score, triggered rules, narrative paragraphs, sentence evidence, and validation checks.
4. Support analyst edits, approval, rejection comments, replay, audit review, and PDF download.
5. Handle loading, empty, success, unauthorized, not-found, and server-error states.
6. Keep pages usable on desktop and smaller screens without hiding critical compliance information.
7. Avoid duplicating API request code across pages; add shared behavior to `api.js`.

## API integration map

| Screen | Backend calls |
| --- | --- |
| Login | `POST /login` |
| New case | `POST /cases` |
| Dashboard | `GET /cases` |
| Review | `GET /cases/{case_id}`, `POST /cases/{case_id}/review`, `POST /cases/{case_id}/replay`, `GET /cases/{case_id}/export/pdf` |
| Audit | `GET /cases/{case_id}/audit` |

Every protected request must include:

```javascript
const token = sessionStorage.getItem("access_token");
fetch(`${API_BASE}/cases`, {
  headers: { Authorization: `Bearer ${token}` }
});
```

Use the existing helper in `api.js` when possible so a `401` can consistently return the user to login.

## UI behavior requirements

- Show the case identifier and current status on every case-specific screen.
- Distinguish `LOW`, `MEDIUM`, and `HIGH` risk using both text and visual styling; do not rely on color alone.
- Keep validation failures visible next to the narrative and never present an unvalidated narrative as approved.
- Require a review comment when the backend requires one; still treat the backend as the source of truth.
- Escape or safely insert narrative text. Generated content must not be inserted as unsanitized HTML.
- Disable controls while a request is in progress and restore them after success or failure.
- Preserve useful form state when a request fails so analysts do not have to re-enter a large alert.

## Example contribution

Use a shared API helper and explicit state handling:

```javascript
async function submitReview(caseId, decision, comment, narrative) {
  const response = await apiRequest(`/cases/${caseId}/review`, {
    method: "POST",
    body: JSON.stringify({ decision, comment, narrative })
  });

  if (!response.ok) {
    throw new Error(await getApiError(response));
  }
  return response.json();
}
```

Adapt the payload to the actual backend schema. Do not invent frontend-only status values.

## Testing responsibilities

Use a local server and manually verify the full browser flow:

```powershell
uvicorn backend.app:app --reload
```

Check login, invalid login, alert preview, successful submission, empty dashboard, case detail, validation failure display, edit and review actions, audit timeline, replay, and PDF download. Test a narrow viewport as well as desktop.

When adding complex JavaScript, extract pure formatting or transformation functions so they can be tested without a browser. Keep API contracts synchronized with `backend/schemas.py`.

## Handoff with other members

- **Backend member:** agree on endpoint paths, request bodies, response fields, error format, and status values before UI changes.
- **AI member:** display structured sentence evidence and validation metadata without changing or reinterpreting the evidence IDs.
- **Database member:** do not depend directly on database fields; consume API responses only.

## Definition of done

- The new or changed workflow has loading, success, empty, and error states.
- No sensitive token or secret is written to the page or console.
- Narrative and audit content is rendered safely.
- The UI works with the actual backend response, including rejected or partially failed cases.
- The flow has been checked at desktop and narrow viewport sizes.
