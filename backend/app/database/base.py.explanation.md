# base.py

Source: [backend/app/database/base.py](base.py)

## A. File Purpose
Provides the base class for all table classes, and helpers for the column types used repeatedly.

## B. Why This File Exists
Every table should name constraints the same way and store identifiers, timestamps and enums the same way. Defining that once prevents small differences from building up.

## C. Dependencies
- **Libraries:** `sqlalchemy`, `enum`, `uuid`, `datetime`.
- **Internal modules:** none.
- **External services / database:** none directly.
- **Depended on by:** all of `app/models/`, and `migrations/env.py`.

## D. Every Function Explained

### `enum_type`
- **Purpose:** define how an enum is stored.
- **Parameters / types:** `enum_class: type[enum.Enum]`, `name: str`. **Returns / type:** `sqlalchemy.Enum`.
- **Internal processing:** uses a text column with a CHECK constraint rather than a PostgreSQL enum type. `values_callable` stores the value (`FLAG_FOR_REVIEW`), not the Python member name.
- **Error handling:** the database refuses values outside the list.
- **Calls:** `sqlalchemy.Enum`. **Used by:** model classes.

### `uuid_primary_key`
- **Purpose:** define a random identifier column.
- **Parameters / types:** none. **Returns / type:** a mapped column.
- **Internal processing:** the application generates it with `uuid.uuid4`, so related rows can be built before anything is sent to the database.
- **Error handling:** none needed.
- **Calls:** `mapped_column`. **Used by:** model classes.

### `created_at_column`
- **Purpose:** define a creation timestamp.
- **Parameters / types:** none. **Returns / type:** a mapped column.
- **Internal processing:** the database sets it with `now()`, and it is timezone-aware.
- **Error handling:** none needed.
- **Calls:** `mapped_column`. **Used by:** model classes.

## E. Classes Explained

### `Base`
- **Purpose:** parent of all table classes, carrying the shared metadata. **Attributes:** `metadata`, with `NAMING_CONVENTION`. **Methods:** none added. **Inheritance:** `sqlalchemy.orm.DeclarativeBase`.

## F. Execution Flow
Imported when model classes are defined. Alembic reads `Base.metadata` to compare models with the database.

## G. Input and Output
No runtime input. Output: table definitions.

## H. Important Technical Concepts
- **Naming convention:** without one, the database invents constraint names, and later migrations cannot reliably refer to them.
- **Text plus CHECK rather than a native enum:** adding a value later takes a simple constraint change, whereas native enum changes have more restrictions.

## I. Example
```python
class Example(Base):
    __tablename__ = "examples"
    id: Mapped[uuid.UUID] = uuid_primary_key()
    created_at: Mapped[datetime] = created_at_column()
```

## J. Maintenance Notes
Changing `NAMING_CONVENTION` would make models disagree with existing constraint names, so it needs a migration.

## K. Related Files
- [session.py](session.py.explanation.md): connects to the database.
- [enums.py](../models/enums.py.explanation.md): the enums stored with `enum_type`.
- [env.py](../../migrations/env.py.explanation.md): uses `Base.metadata`.
