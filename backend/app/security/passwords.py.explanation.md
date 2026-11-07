# passwords.py

Source: [backend/app/security/passwords.py](passwords.py)

## A. File Purpose
Hashes and verifies user passwords.

## B. Why This File Exists
PRD sections 9.2 and 10 require secure hashing and forbid storing plaintext passwords.

## C. Dependencies
- **Libraries:** `argon2-cffi`.
- **Internal modules:** none.
- **External services / database:** none.
- **Depended on by:** `auth_service.py`.

## D. Every Function Explained

### `hash_password`
- **Purpose:** create a hash for storage.
- **Parameters / types:** `password: str`. **Returns / type:** `str`, which includes the salt and cost settings.
- **Internal processing:** Argon2id with the library's default costs.
- **Error handling:** none needed. **Calls:** `PasswordHasher.hash`. **Used by:** `auth_service`.

### `verify_password`
- **Purpose:** check a password against a stored hash.
- **Parameters / types:** `password_hash: str`, `password: str`. **Returns / type:** `bool`.
- **Internal processing:** the library compares in constant time.
- **Error handling:** a mismatch or damaged hash returns `False`, so login cannot fail with a server error.
- **Calls:** `PasswordHasher.verify`. **Used by:** `auth_service`, `verify_against_dummy`.

### `verify_against_dummy`
- **Purpose:** take the same time when the email is unknown.
- **Parameters / types:** `password: str`. **Returns / type:** `None`.
- **Internal processing:** verifies against `_DUMMY_HASH` and discards the result.
- **Error handling:** none needed. **Calls:** `verify_password`. **Used by:** `auth_service`.

## E. Classes Explained
None.

## F. Execution Flow
Importing the module creates the dummy hash once. After that, functions run on request.

## G. Input and Output
Input: passwords. Output: hashes or a true/false result.

## H. Important Technical Concepts
- **Argon2id:** deliberately slow and memory-hard, which makes large-scale guessing expensive if hashes ever leak.
- **Salt:** random per hash and stored inside it, so identical passwords produce different hashes.
- **Timing:** without the dummy check, a fast "no such user" response would reveal which emails have accounts.

## I. Example
```python
stored = hash_password("a long passphrase")
verify_password(stored, "a long passphrase")  # True
```

## J. Maintenance Notes
Raising cost settings later affects new hashes only. Old ones keep working, since each hash records its own settings.

## K. Related Files
- [auth_service.py](../services/auth_service.py.explanation.md): uses these functions.
- [tokens.py](tokens.py.explanation.md): what a successful login receives.
