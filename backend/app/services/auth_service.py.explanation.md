# auth_service.py

Source: [backend/app/services/auth_service.py](auth_service.py)

## A. File Purpose
Holds the rules for signing in, creating and updating accounts, and changing passwords.

## B. Why This File Exists
PRD 8.1 keeps business logic out of routes. PRD 2.3 has administrators managing permitted users, and that needs safeguards such as not removing the last administrator.

## C. Dependencies
- **Libraries:** `sqlalchemy`.
- **Internal modules:** `app.core`, `app.models`, `app.security.passwords`, `app.security.tokens`, `app.services.audit_service`.
- **External services / database:** `users`, `audit_logs`.
- **Depended on by:** auth and user routes, `scripts/create_admin.py`.

## D. Every Function Explained

### `normalise_email`
Trims and lower-cases an email, so one person cannot hold two accounts through capitalisation.

### `authenticate`
Returns a bearer token for correct credentials, for `/auth/login`, by calling `verify_login`.

### `verify_login`
- **Purpose:** check credentials, for both sign-in routes.
- **Parameters / types:** `session`, `email: str`, `password: str`, `client_address: str`. **Returns / type:** `User`.
- **Internal processing:** checks the rate limit first. For an unknown email it still spends the time of a password check. Only failures count towards the limit, and success clears them.
- **Error handling:** wrong email, wrong password and inactive account all raise the same error. `RateLimitedError` when limited.
- **Calls:** `limiter`, `verify_password`, `verify_against_dummy`, `record_event`. **Used by:** `authenticate`, the session route.

### `list_assignable`
Returns active investigators and admins, ordered by email, for the assignee list.

### `create_user`
- **Purpose:** create an account.
- **Parameters / types:** `session`, `email`, `password`, `role: UserRole`, `created_by`. **Returns / type:** `User`.
- **Internal processing:** relies on the unique constraint rather than a prior lookup, which avoids a race between two requests.
- **Error handling:** raises `ConflictError` for a used email.
- **Calls:** `hash_password`, `record_event`. **Used by:** the users route, `create_admin.py`.

### `list_users`
Returns one page of accounts and the total count, in creation order.

### `_require_another_active_admin`
- **Purpose:** prevent lockout.
- **Parameters / types:** `session`, `user: User`. **Returns / type:** `None`.
- **Internal processing:** locks admin rows, then checks whether this user is the only one.
- **Error handling:** raises `InvalidInputError`.
- **Calls:** `session.scalars`. **Used by:** `update_user`.

### `update_user`
- **Purpose:** change a role or active state.
- **Parameters / types:** `session`, `user_id`, `role`, `is_active`, `changed_by`. **Returns / type:** `User`.
- **Internal processing:** refuses to let users deactivate their own account, then applies the last-administrator rule, and records only actual changes in the audit log.
- **Error handling:** `NotFoundError`, `InvalidInputError` for self-deactivation (added in M7: the interface disabled the button, but the API had allowed it while another administrator existed), or the lockout refusal.
- **Calls:** `_require_another_active_admin`, `record_event`. **Used by:** the users route.

### `change_password`
- **Purpose:** change the caller's own password.
- **Parameters / types:** `session`, `user: User`, `current: str`, `new: str`. **Returns / type:** `None`.
- **Internal processing:** verifies the current password, stores a new hash and raises `token_version`.
- **Error handling:** raises `AuthenticationError` for a wrong current password.
- **Calls:** `verify_password`, `hash_password`, `record_event`. **Used by:** the auth route.

## E. Classes Explained
None.

## F. Execution Flow
A route calls one function, which applies its rules, writes an audit entry and commits.

## G. Input and Output
Input: credentials or account changes. Output: tokens or `User` rows.

## H. Important Technical Concepts
- **Rate limit key:** client address plus email. A single address cannot guess one account quickly, and one attacker cannot lock out a real user from elsewhere.
- **No self-registration:** accounts are created by an administrator, or by `create_admin.py` for the first one.

## I. Example
```python
token = authenticate(session, "ana@example.com", "a long passphrase", "127.0.0.1")
```

## J. Maintenance Notes
Behind a proxy, `client_address` will be the proxy unless the server is told to trust forwarded headers. Phase 6 needs to configure this, or the limit would be shared by all users.

## K. Related Files
- [passwords.py](../security/passwords.py.explanation.md): hashing.
- [auth.py](../api/routes/auth.py.explanation.md), [users.py](../api/routes/users.py.explanation.md): routes.
- [create_admin.py](../../../scripts/create_admin.py.explanation.md): the first account.
