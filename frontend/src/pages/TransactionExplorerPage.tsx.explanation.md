# TransactionExplorerPage.tsx

Source: [frontend/src/pages/TransactionExplorerPage.tsx](TransactionExplorerPage.tsx)

## A. File Purpose
Page 4 of PRD 7.4, covering PRD 6.5: a searchable table of stored predictions with every PRD filter, sorting, paging and a detail view.

## B. Why This File Exists
PRD 6.5 lists the filters: identifier, risk level, decision, type, amount range, simulation time and investigation status.

## C. Dependencies
- **Libraries:** React.
- **Internal modules:** components, `../hooks/useApiResource.ts`, `../services/endpoints.ts`, `../utils/format.ts`.
- **External services / database:** `GET /api/v1/transactions`.
- **Depended on by:** `registry.tsx`.

## D. Every Function Explained

### `toQuery`
Turns the form into API query parameters, trimming the identifier and leaving blank filters out.

### `Select`
A labelled select used for each choice filter.

### `TransactionExplorerPage`
Keeps a draft and an applied set of filters, so typing does not send a request per keystroke. Loads the applied page, and shows the table, pager and detail panel.

### `set`
Returns a change handler for one filter field.

### `apply`
Applies the draft filters and returns to the first page.

### `reset`
Clears all filters.

## E. Classes Explained
None.

## F. Execution Flow
Change filters, apply, the page loads, then open a row for its detail.

## G. Input and Output
Input: filters, sorting and paging. Output: 25 rows per page, and the detail panel.

## H. Important Technical Concepts
- **`EMPTY_FILTERS`** is the default state: newest first, no filters.
- **The API validates filters too,** so a hand-edited request cannot bypass them.

## I. Example
```ts
toQuery({ ...EMPTY_FILTERS, riskLevel: "HIGH" }, 0);
```

## J. Maintenance Notes
A new filter needs a field here, a parameter in `toQuery`, and API support.

## K. Related Files
- [transactions.py repository](../../../backend/app/repositories/transactions.py.explanation.md): the query.
- [TransactionDetailPanel.tsx](../components/TransactionDetailPanel.tsx.explanation.md): the detail view.
