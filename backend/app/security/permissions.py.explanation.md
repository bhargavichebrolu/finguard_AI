# permissions.py

Source: [backend/app/security/permissions.py](permissions.py)

## A. File Purpose
Defines every action that needs authorisation, and which roles may do it.

## B. Why This File Exists
PRD section 10 requires role-based permissions. One table means authorisation can be read and tested in one place, rather than being scattered through routes.

## C. Dependencies
- **Libraries:** `enum`.
- **Internal modules:** `app.models.enums`.
- **External services / database:** none.
- **Depended on by:** `security/dependencies.py`, and routes that name a permission.

## D. Every Function Explained

### `has_permission`
- **Purpose:** answer whether a role may do something.
- **Parameters / types:** `role: UserRole`, `permission: Permission`. **Returns / type:** `bool`.
- **Internal processing:** looks it up in `ROLE_PERMISSIONS`.
- **Error handling:** an unknown role raises `KeyError`, which fails closed.
- **Calls:** none. **Used by:** `require_permission`.

## E. Classes Explained

### `Permission`
- **Purpose:** the list of controlled actions. **Inheritance:** `enum.StrEnum`.

## F. Execution Flow
A route declares `require_permission(Permission.X)`, and the dependency calls `has_permission`.

## G. Input and Output

| Action | Demo | Analyst | Investigator | Admin |
|---|---|---|---|---|
| Predict, upload batch, view transactions, models, summary, settings, status | Yes | Yes | Yes | Yes |
| View investigations, export reports | No | Yes | Yes | Yes |
| Update investigations, add notes | No | No | Yes | Yes |
| Change settings, manage users, view audit log | No | No | No | Yes |

## H. Important Technical Concepts
- **Mapping from PRD section 2:** demo matches 2.4, analyst 2.1, investigator 2.2, and admin 2.3. PRD 2.1 says analysts "investigate", read here as viewing and filtering, because status and notes are listed for the investigator in 2.2.
- **Demo data is separate.** Demo users see only demo records, and everyone else sees only non-demo records. That scoping is applied in repositories, not here.
- **Admin gets all permissions** through `frozenset(Permission)`, so a new permission reaches admins automatically and no one else.

## I. Example
```python
has_permission(UserRole.ANALYST, Permission.UPDATE_INVESTIGATIONS)  # False
```

## J. Maintenance Notes
Adding a permission means adding it here and to the table above. `test_permissions_matrix` lists every combination, so it must be updated deliberately.

## K. Related Files
- [dependencies.py](dependencies.py.explanation.md): enforces this.
- [enums.py](../models/enums.py.explanation.md): the roles.
