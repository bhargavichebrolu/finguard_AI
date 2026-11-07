# transactions.py (repository)

Source: [backend/app/repositories/transactions.py](transactions.py)

## A. File Purpose
Holds the database queries for listing and reading transactions.

## B. Why This File Exists
PRD 8.1 separates database operations from business logic. The explorer's filters from PRD 6.5 make a query long enough to deserve its own home, and batch results reuse it.

## C. Dependencies
- **Libraries:** `sqlalchemy`.
- **Internal modules:** `app.models`.
- **External services / database:** `transactions`, `predictions`, `investigations`.
- **Depended on by:** the transactions, batches and reports code.

## D. Every Function Explained

### `_escape_like`
- **Purpose:** treat `%` and `_` in a search term as ordinary characters.
- **Parameters / types:** `text: str`. **Returns / type:** `str`.
- **Internal processing:** escapes them with a backslash.
- **Error handling:** none needed. **Calls:** none. **Used by:** `_apply_filters`.

### `_base_query`
- **Purpose:** join the three tables and apply demo separation.
- **Parameters / types:** `is_demo: bool`. **Returns / type:** `Select`.
- **Internal processing:** an outer join on investigations, since unflagged rows have none.
- **Error handling:** none needed. **Calls:** `select`. **Used by:** the public functions.

### `_apply_filters`
- **Purpose:** add a condition for each filter that is set.
- **Parameters / types:** `query`, `filters`. **Returns / type:** `Select`.
- **Internal processing:** every value is passed as a bound parameter, so no input becomes part of the SQL text.
- **Error handling:** none needed. **Calls:** none. **Used by:** `list_transactions`.

### `list_transactions`
- **Purpose:** return a page and the total.
- **Parameters / types:** `session`, `is_demo`, `filters`, `sort_by`, `sort_order`, `limit`, `offset`. **Returns / type:** `tuple[list[Row], int]`.
- **Internal processing:** counts over a subquery, then sorts using a fixed column map, with the identifier breaking ties.
- **Error handling:** invalid sort names are refused earlier by the route's `Literal` type.
- **Calls:** `_base_query`, `_apply_filters`. **Used by:** the transactions and batches routes.

### `get_transaction`
- **Purpose:** return one row for the detail view.
- **Parameters / types:** `session`, `transaction_id`, `is_demo`. **Returns / type:** `Row | None`.
- **Internal processing:** loads notes and history in extra queries.
- **Error handling:** returns `None` if missing or in the other scope.
- **Calls:** `_base_query`. **Used by:** the transactions route.

## E. Classes Explained

### `TransactionFilters`
- **Purpose:** all PRD 6.5 filters, plus the batch link. **Attributes:** one field per filter. **Methods:** none. **Inheritance:** none; a frozen dataclass.

## F. Execution Flow
The route builds `TransactionFilters`, then calls `list_transactions`.

## G. Input and Output
Input: filters and paging. Output: rows of `(Transaction, Prediction, Investigation | None)`.

## H. Important Technical Concepts
- **Stable paging:** without a tie-breaker, rows with equal values could move between pages.
- **Offset paging:** simple and enough for this scale, though large offsets get slower.
- **Other simple queries live in services.** Repositories hold the multi-table queries, and one-line lookups such as a user by email stay in their service.

## I. Example
```python
list_transactions(
    session, False, TransactionFilters(risk_level=RiskLevel.HIGH), "model_score", "desc", 50, 0
)
```

## J. Maintenance Notes
A new sortable column must go in both `SortField` and `_SORT_COLUMNS`. Columns used for filtering need an index, added through a migration.

## K. Related Files
- [transactions.py route](../api/routes/transactions.py.explanation.md): the caller.
- [records.py](../models/records.py.explanation.md): the tables and indexes.
