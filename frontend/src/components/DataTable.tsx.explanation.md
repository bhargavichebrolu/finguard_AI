# DataTable.tsx

Source: [frontend/src/components/DataTable.tsx](DataTable.tsx)

## A. File Purpose
A generic table with a hidden caption, an empty state, optional row selection, and a pager.

## B. Why This File Exists
The explorer, investigation queue, batch results, experiment history and audit log are all tables. Sharing one keeps headers, numeric alignment, empty states and paging consistent.

## C. Dependencies
- **Libraries:** React, `lucide-react`.
- **Internal modules:** `feedback.tsx`, `../utils/format.ts`.
- **External services / database:** none.
- **Depended on by:** pages with lists.

## D. Every Function Explained

### `DataTable`
- **Purpose:** render rows with column definitions.
- **Parameters / types:** `caption`, `columns: Column<T>[]`, `rows`, `rowKey`, `emptyTitle`, `emptyMessage`, `onRowSelect`, `selectedKey`. **Returns / type:** a table, or `EmptyState` when there are no rows.
- **Internal processing:** numeric columns are right-aligned with tabular figures. With `onRowSelect` each row gets an "Open" button.
- **Error handling:** none needed. **Calls:** `EmptyState`. **Used by:** pages.

### `Pager`
Shows "first to last of total", with previous and next buttons disabled at the ends.

### `TableScroll`
- **Purpose:** the scrolling area around a wide table.
- **Parameters / types:** `label`, `children`. **Returns / type:** a focusable `div` with `role="group"` named "<label>, scrollable table".
- **Internal processing:** `tabIndex=0` lets keyboard users focus it and scroll with the arrow keys (WCAG 2.1.1, axe `scrollable-region-focusable`). Its class is positioned, so visually hidden text inside the table is clipped here.
- **Error handling:** none. **Calls:** none. **Used by:** `DataTable`, `ChartCard`, `ExplanationPanel`, `ExplainabilityPage`, `ModelPerformancePage`.

## E. Classes Explained
None.

## F. Execution Flow
A page passes rows from the API and a column list.

## G. Input and Output
Input: rows and columns. Output: an accessible table.

## H. Important Technical Concepts
- **Why a group, not a region:** a region would add a page landmark for every table; a named group gives the focus stop a name without that.
- **Buttons, not clickable rows:** an explicit "Open" button works with a keyboard and screen readers, and a clickable `<tr>` does not.

## I. Example
```tsx
<DataTable caption="Transactions" columns={columns} rows={page.items} rowKey={(row) => row.transaction_id} emptyTitle="No transactions" />
```

## J. Maintenance Notes
Wide tables scroll inside `.table-wrap`, so pages never scroll sideways on phones.

## K. Related Files
- [feedback.tsx](feedback.tsx.explanation.md): the empty state.
- [components.css](../styles/components.css.explanation.md): table styles.
