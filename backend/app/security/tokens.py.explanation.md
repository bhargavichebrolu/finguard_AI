# tokens.py

Source: [backend/app/security/tokens.py](tokens.py)

## A. File Purpose
Creates and verifies the signed tokens a client sends after logging in.

## B. Why This File Exists
PRD section 10 requires authentication. Tokens let the API confirm who is calling without storing sessions.

## C. Dependencies
- **Libraries:** `pyjwt`, `datetime`, `uuid`.
- **Internal modules:** `app.core.config`, `app.core.errors`.
- **External services / database:** none.
- **Depended on by:** `auth_service.py`, `security/dependencies.py`.

## D. Every Function Explained

### `create_access_token`
- **Purpose:** issue a token.
- **Parameters / types:** `user_id: uuid.UUID`, `token_version: int`. **Returns / type:** `str`.
- **Internal processing:** signs the user ID, token version, issue time and expiry with `SECRET_KEY`.
- **Error handling:** none needed. **Calls:** `jwt.encode`. **Used by:** `auth_service`, tests.

### `decode_access_token`
- **Purpose:** verify a token.
- **Parameters / types:** `token: str`. **Returns / type:** `TokenClaims`.
- **Internal processing:** checks signature, expiry and that all claims exist. Only HS256 is accepted.
- **Error handling:** every failure raises the same `AuthenticationError`, so callers learn nothing about why.
- **Calls:** `jwt.decode`. **Used by:** `get_current_user`.

## E. Classes Explained

### `TokenClaims`
- **Purpose:** verified values. **Attributes:** `user_id`, `token_version`. **Methods:** none. **Inheritance:** `NamedTuple`.

## F. Execution Flow
Login calls `create_access_token`. Each later request calls `decode_access_token`, then loads the user.

## G. Input and Output
Input: a user's identifiers or a token. Output: a token or verified claims.

## H. Important Technical Concepts
- **The role is not in the token.** It is read from the database per request, so a role change or deactivation takes effect immediately instead of at expiry.
- **`ver`:** compared with `users.token_version`. Changing a password increases that value, which invalidates earlier tokens.
- **Fixed algorithm list:** prevents an attacker choosing `none` or another algorithm in the token's own header.

## I. Example
```python
token = create_access_token(user.id, user.token_version)
decode_access_token(token).user_id == user.id  # True
```

## J. Maintenance Notes
Changing `SECRET_KEY` invalidates all tokens, which is the way to log everyone out. Phase 4 must keep tokens out of places scripts from other sites can read.

## K. Related Files
- [dependencies.py](dependencies.py.explanation.md): uses `decode_access_token`.
- [ADR 0003](../../../docs/decisions/0003-phase-3-decisions.md): decision 12.
