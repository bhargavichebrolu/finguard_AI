# SystemInformationPage.tsx

Source: [frontend/src/pages/SystemInformationPage.tsx](SystemInformationPage.tsx)

## A. File Purpose
Page 10 of PRD 7.4. Shows service health, the frozen model's identity and, for administrators, the audit log.

## B. Why This File Exists
PRD 2.3 and 6.10 have administrators inspect system health and activity. Showing the model hash and threshold also lets anyone confirm which model is serving.

## C. Dependencies
- **Libraries:** React.
- **Internal modules:** `../components`, `../hooks`, `../services/endpoints.ts`, `../utils/format.ts`.
- **External services / database:** `GET /api/v1/system/status`, `GET /health`, `GET /api/v1/audit-logs`.
- **Depended on by:** `registry.tsx`.

## D. Every Function Explained

### `SystemInformationPage`
Loads status and health, shows service facts and the frozen model's version, threshold (marked as frozen) and SHA-256, and includes the audit log when the role has `view_audit_log`.

### `AuditLog`
Pages through audit entries, 20 at a time, newest first.

## E. Classes Explained
None.

## F. Execution Flow
Two requests load on open. The audit log loads its own pages.

## G. Input and Output
Output: two fact cards and an optional table.

## H. Important Technical Concepts
- **The threshold is shown, not editable.** It is frozen in code, and the page says so.

## I. Example
```tsx
<SystemInformationPage />
```

## J. Maintenance Notes
Keep this page free of interpreted performance claims. It reports state only.

## K. Related Files
- [health.py](../../../backend/app/api/routes/health.py.explanation.md): the status route.
- [audit.py](../../../backend/app/api/routes/audit.py.explanation.md): the audit route.
