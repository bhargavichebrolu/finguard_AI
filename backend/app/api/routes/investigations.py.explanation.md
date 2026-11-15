# investigations.py (routes)

Source: [backend/app/api/routes/investigations.py](investigations.py)

## A. File Purpose
Exposes listing, reading and updating investigations, and adding notes.

## B. Why This File Exists
These are the PRD 8.2 investigation endpoints. `GET /investigations/{id}` is an addition, so a client can read notes and history directly.

## C. Dependencies
- **Libraries:** `fastapi`.
- **Internal modules:** `app.api.schemas`, `app.core.errors`, `app.repositories.investigations`, `app.security`, `app.services.investigation_service`.
- **External services / database:** through the service and repository.
- **Depended on by:** `app/api/router.py`.

## D. Every Function Explained

### `list_all`
`GET /api/v1/investigations`. Filters by `investigation_status` and `assigned_user_id`, and returns a page. Needs `VIEW_INVESTIGATIONS`.

### `read_one`
`GET /api/v1/investigations/{investigation_id}`. Returns notes and history, or 404. Needs `VIEW_INVESTIGATIONS`.

### `update`
`PATCH /api/v1/investigations/{investigation_id}`. Takes `InvestigationUpdate`. Returns 404, or 422 for a bad assignee or an empty body. Needs `UPDATE_INVESTIGATIONS`.

### `add_note`
`POST /api/v1/investigations/{investigation_id}/notes`. Takes `NoteCreate`, and returns the note with status 201. Needs `UPDATE_INVESTIGATIONS`.

## E. Classes Explained
None. `Viewer` and `Investigator` are type aliases carrying the permission checks.

## F. Execution Flow
Permission check, validation, service, response.

## G. Input and Output
See `API_DOCUMENTATION.md`.

## H. Important Technical Concepts
- **409 (Phase 5 M7):** `update` documents the conflict answer given when `expected_status` no longer matches.
- **Two levels of access:** analysts can see the queue but cannot change it, following PRD 2.1 and 2.2.

## I. Example
```powershell
curl.exe -X PATCH -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d "{\"status\": \"UNDER_REVIEW\"}" http://127.0.0.1:8010/api/v1/investigations/<id>
```

## J. Maintenance Notes
Keep rules in the service.

## K. Related Files
- [investigation_service.py](../../services/investigation_service.py.explanation.md): the rules.
- [permissions.py](../../security/permissions.py.explanation.md): access.
