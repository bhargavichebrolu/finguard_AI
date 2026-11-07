# settings.py (routes)

Source: [backend/app/api/routes/settings.py](settings.py)

## A. File Purpose
Exposes current settings, versions and health, and lets administrators change the high risk boundary.

## B. Why This File Exists
These are the PRD 8.2 configuration endpoints, implementing PRD 6.10.

## C. Dependencies
- **Libraries:** `fastapi`, `pydantic`.
- **Internal modules:** `app.core`, `app.database.session`, `app.security`, `app.services.settings_service`.
- **External services / database:** `app_settings`, and saved preprocessing metadata.
- **Depended on by:** `app/api/router.py`.

## D. Every Function Explained

### `_view`
Builds the response from settings, the database and the verified model's saved metadata.

### `read_settings`
`GET /api/v1/settings`. Needs `VIEW_SETTINGS`.

### `update_settings`
`PATCH /api/v1/settings`. Needs `UPDATE_SETTINGS`. A boundary at or below the threshold gives 422, and sending a threshold field gives 422.

## E. Classes Explained

### `DatasetInfo`
The dataset's name, source file, versions and split boundaries. **Inheritance:** `BaseModel`.

### `SettingsView`
All of PRD 6.10. `frozen_threshold_is_editable` is always false, so clients can see why no control exists. **Inheritance:** `BaseModel`.

### `SettingsUpdate`
Only `high_risk_boundary`. `extra="forbid"` refuses anything else. **Inheritance:** `BaseModel`.

## F. Execution Flow
Permission check, validation, service, then a fresh view.

## G. Input and Output
`{"high_risk_boundary": 0.5}` sets the Medium and High line for future predictions.

## H. Important Technical Concepts
- **PRD 6.10's "risk threshold settings" are limited on purpose.** The authorisation forbids changing the threshold, so only the display boundary can move. See ADR 0003, decision 4.

## I. Example
```powershell
curl.exe -X PATCH -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d "{\"high_risk_boundary\": 0.5}" http://127.0.0.1:8010/api/v1/settings
```

## J. Maintenance Notes
A new changeable setting needs validation, an audit entry and a field in `SettingsUpdate`.

## K. Related Files
- [settings_service.py](../../services/settings_service.py.explanation.md): validation and storage.
- [risk.py](../../services/risk.py.explanation.md): how the boundary is used.
