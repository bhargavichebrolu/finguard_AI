# auth.py

Source: [backend/app/api/schemas/auth.py](auth.py)

## A. File Purpose
Defines the request and response shapes for sign-in, account management and the audit log.

## B. Why This File Exists
PRD 8.2 requires schemas on every endpoint. Separate request and response classes also ensure a password can be accepted but never returned.

## C. Dependencies
- **Libraries:** `pydantic`, including `EmailStr`, which uses `email-validator`.
- **Internal modules:** `app.api.schemas.common`, `app.models.enums`, `app.models.records`, `app.security.permissions`.
- **External services / database:** none.
- **Depended on by:** auth, users and audit routes.

## D. Every Function Explained

### `current_user_view`
- **Purpose:** build the signed-in view.
- **Parameters / types:** `user: User`, `session: UserSession | None`. **Returns / type:** `CurrentUserView`.
- **Internal processing:** lists permissions from the single role table, and adds the session's expiry.
- **Error handling:** none needed. **Calls:** `ROLE_PERMISSIONS`. **Used by:** the auth routes.

## E. Classes Explained

### `TokenResponse`
`access_token` and `token_type`. **Inheritance:** `BaseModel`.

### `UserView`
Identifier, email, role, active state and creation time. It has no `password_hash` field, so serialising a user cannot expose one. **Inheritance:** `ApiModel`.

### `CurrentUserView`
`UserView` plus `permissions`, sorted values from `ROLE_PERMISSIONS`, and `session_expires_at`, which is `None` for bearer tokens. **Inheritance:** `UserView`.

### `AssigneeView`
Identifier, email and role only. **Inheritance:** `ApiModel`.

### `SessionCreate`
Email and password for a browser sign-in, as JSON, with extra fields refused. **Inheritance:** `BaseModel`.

### `UserCreate`
Email, password and role. `extra="forbid"` refuses unknown fields. **Inheritance:** `BaseModel`.

### `UserUpdate`
Optional `role` and `is_active`. **Inheritance:** `BaseModel`.

### `PasswordChange`
Current and new password. **Inheritance:** `BaseModel`.

### `AuditLogView`
One entry from `audit_logs`. **Inheritance:** `ApiModel`.

## F. Execution Flow
FastAPI validates requests against these classes before the route runs, and filters responses through them afterwards.

## G. Input and Output
For example, `UserCreate` takes `{"email": "a@example.com", "password": "...", "role": "analyst"}`.

## H. Important Technical Concepts
- **Password length:** a 12-character minimum favours passphrases. The 128 maximum stops very long inputs being used to make hashing expensive.
- **Rejected passwords are not echoed.** `errors.py` removes submitted values from validation errors.

## I. Example
```json
{"current_password": "old passphrase here", "new_password": "a new long passphrase"}
```

## J. Maintenance Notes
Do not add secret fields to any `View` class.

## K. Related Files
- [common.py](common.py.explanation.md): base classes.
- [auth_service.py](../../services/auth_service.py.explanation.md): the rules.
