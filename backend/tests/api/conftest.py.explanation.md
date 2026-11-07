# conftest.py (API tests)

Source: [backend/tests/api/conftest.py](conftest.py)

## A. File Purpose
Provides the fixtures API tests share: the application, a prepared database and test users.

## B. Why This File Exists
API tests should exercise the real stack. These fixtures start the real application with the frozen model and connect it to real PostgreSQL, with nothing mocked.

## C. Dependencies
- **Libraries:** `pytest`, `fastapi.testclient`, `sqlalchemy`.
- **Internal modules:** `app.main`, `app.core.rate_limit`, `app.models`, `app.security`, `app.services.model_service`, `tests/conftest.py`.
- **External services / database:** PostgreSQL through `TEST_DATABASE_URL`, and the frozen model.
- **Depended on by:** every test under `tests/api/`.

## D. Every Function Explained

### `app_client`
Session fixture. Starts the application once through `TestClient`, which runs `lifespan`, so the model is verified exactly as in production. Skips if the model file is absent.

### `session`
Empties all tables, resets rate limits, registers the model again and yields a session. Each test therefore starts clean. Takes `db_engine` and `app_client`.

### `client`
Returns `app_client`, after `session` has prepared the database.

### `make_user`
Returns the factory `_make`, which stores a user with a role.

### `_make`
Creates and commits a `User`. Parameters: `role`, `email`, and other column values. Returns `User`.

### `headers_for`
Returns the factory `_headers`.

### `_headers`
Creates a user with the given role and returns an `Authorization` header holding a real signed token.

## E. Classes Explained
None.

## F. Execution Flow
pytest starts the application once, then runs `session` before each test.

## G. Input and Output
Input: the test database. Output: objects passed to tests.

## H. Important Technical Concepts
- **Shared password hash:** Argon2 is deliberately slow, and hashing once for all test users keeps tests quick. `test_auth.py` tests hashing itself.
- **Tokens made directly:** most tests skip the login request for speed. `test_auth.py` tests the real login.

## I. Example
```python
def test_example(client, headers_for):
    response = client.get("/api/v1/auth/me", headers=headers_for(UserRole.ADMIN))
```

## J. Maintenance Notes
These fixtures delete all rows, which is why `require_test_database_name` guards the database name.

## K. Related Files
- [test_auth.py](test_auth.py.explanation.md): uses these fixtures.
- [main.py](../../app/main.py.explanation.md): the application.
