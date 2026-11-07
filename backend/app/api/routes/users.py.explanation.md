# users.py

Source: [backend/app/api/routes/users.py](users.py)

## A. File Purpose
Lets administrators list, create and update accounts.

## B. Why This File Exists
PRD 2.3 includes managing permitted users. These routes are an addition to the PRD 8.2 list, permitted by section 13.

## C. Dependencies
- **Libraries:** `fastapi`.
- **Internal modules:** `app.api.schemas`, `app.security`, `app.services.auth_service`.
- **External services / database:** through the service.
- **Depended on by:** `app/api/router.py`.

## D. Every Function Explained

### `list_users`
`GET /api/v1/users`. Takes `limit` and `offset`, and returns `Page[UserView]`. Non-admins get 403.

### `create_user`
`POST /api/v1/users`. Takes `UserCreate`, and returns `UserView` with status 201. A used email gives 409, and a short password gives 422 without echoing it.

### `update_user`
`PATCH /api/v1/users/{user_id}`. Takes `UserUpdate`, and returns `UserView`. An unknown user gives 404, and removing the last administrator gives 422.

All three call `auth_service` and are used by clients.

## E. Classes Explained
None. `AdminUser` is a type alias for a user holding `MANAGE_USERS`.

## F. Execution Flow
The permission check runs first, then the route calls the service.

## G. Input and Output
Input: JSON bodies and query parameters. Output: account records without password hashes.

## H. Important Technical Concepts
- **`_admin` in `list_users`:** the value is unused, but declaring it is what enforces the check.

## I. Example
```json
{"email": "ana@example.com", "password": "a long passphrase", "role": "investigator"}
```

## J. Maintenance Notes
There is no delete route. Deactivating keeps the record of who did what.

## K. Related Files
- [auth_service.py](../../services/auth_service.py.explanation.md): the rules.
- [permissions.py](../../security/permissions.py.explanation.md): the role table.
