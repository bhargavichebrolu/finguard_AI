# SettingsPage.tsx

Source: [frontend/src/pages/SettingsPage.tsx](SettingsPage.tsx)

## A. File Purpose
Page 9 of PRD 7.4, covering PRD 6.10: current settings, versions and dataset; a password change for everyone; and, for administrators, the high risk boundary and account management.

## B. Why This File Exists
PRD 6.10 lists the risk threshold, model version, dataset and user management. The frozen review threshold is shown but cannot be changed, because the authorisation forbids changing thresholds. Only the line between Medium and High can move.

## C. Dependencies
- **Libraries:** React.
- **Internal modules:** `feedback.tsx`, `DataTable.tsx`, `../hooks/useApiResource.ts`, `../hooks/useAuth.tsx`, `../services/api.ts`, `../services/endpoints.ts`, `../utils/format.ts`.
- **External services / database:** `GET`, `PATCH /api/v1/settings`, `POST /api/v1/auth/change-password`, `GET`, `POST /api/v1/users`, `PATCH /api/v1/users/{id}`.
- **Depended on by:** `registry.tsx`.

## D. Every Function Explained

### `checkBoundary`
- **Purpose:** check a proposed high risk boundary before sending it.
- **Parameters / types:** `text: string`, `frozenThreshold: number`. **Returns / type:** an error message, or `null` when valid.
- **Internal processing:** the value must be a number above the frozen threshold and at most 1, the same rule the API applies.
- **Error handling:** returns a message. **Calls:** `formatScore`. **Used by:** `BoundaryForm`, tests.

### `SettingsPage`
Loads the settings, then shows the facts, the boundary form if the user has `update_settings`, the password form, and account management if the user has `manage_users`.

### `SettingsFacts`
Two cards: the review threshold (marked frozen), the high risk boundary and the risk band description; and the application and model versions, database availability, upload limits and dataset.

### `BoundaryForm`
An input for the new boundary. A valid value opens a confirmation explaining the change is audited, and confirming saves it and reloads the settings.

### `PasswordForm`
Current and new password fields, with the 12-character minimum shown as a hint. Success signs the user out, because the API revokes every session when the password changes.

### `UserManagement`
A paged table of accounts. Each row has a role select and a Deactivate or Reactivate button. Deactivation asks for confirmation, and an administrator cannot deactivate their own account.

### `change`
Nested in `UserManagement`. Sends one account change, then reloads the list, or shows the error.

### `CreateUserForm`
Email, temporary password and role. The button stays disabled until the password is long enough. On success the form clears and tells the administrator to share the password privately.

### `submit`
Three nested handlers: in `BoundaryForm` it validates and asks for confirmation; in `PasswordForm` and `CreateUserForm` it sends the request.

### `save`
Nested in `BoundaryForm`. Sends the new boundary after confirmation.

### `user`
A local value in `CreateUserForm.submit`, not a function: the created account.

## E. Classes Explained
None.

## F. Execution Flow
Load settings; each form sends its own request and reloads what it changed.

## G. Input and Output
Input: form values. Output: saved settings and accounts, and audit entries written by the API.

## H. Important Technical Concepts
- **Interface and API agree, the API decides:** the controls are hidden from roles without permission, and the API refuses the request anyway if they are not.
- **Passwords are never echoed:** no password is shown after creation, and the fields use `autoComplete` so password managers work.

## I. Example
```ts
checkBoundary("0.45", settings.frozen_threshold) // null when valid
```

## J. Maintenance Notes
Keep `MIN_PASSWORD` equal to the API's minimum and `ROLES` equal to the `Role` enum.

## K. Related Files
- [settings.py](../../../backend/app/api/routes/settings.py.explanation.md): the settings route.
- [users.py](../../../backend/app/api/routes/users.py.explanation.md): account routes.
