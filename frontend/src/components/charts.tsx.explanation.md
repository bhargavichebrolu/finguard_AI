# charts.tsx

Source: [frontend/src/components/charts.tsx](charts.tsx)

## A. File Purpose
Chart building blocks: a card that swaps any chart for a table, single-series bars, paired bars, a trend line, contribution bars and a stat tile.

## B. Why This File Exists
PRD 6.1 and 6.8 need many charts. Building them from a few consistent pieces keeps marks thin, grids quiet and every chart readable as a table, which also serves screen-reader and keyboard users.

## C. Dependencies
- **Libraries:** React, Recharts.
- **Internal modules:** `../utils/chartColors.ts`, `../utils/format.ts`.
- **External services / database:** none.
- **Depended on by:** Dashboard, Explainable AI, Model Performance, `ExplanationPanel.tsx`.

## D. Every Function Explained

### `ChartCard`
- **Purpose:** frame a chart with a title, description and a "Show table" button.
- **Parameters / types:** `title`, `description`, `tableColumns`, `tableRows`, `children`. **Returns / type:** an `<article>`.
- **Internal processing:** the button toggles between the chart and a table of the same values, with `aria-pressed` showing the state. The chart is hidden from assistive technology, because the table carries the same information.
- **Error handling:** none needed. **Calls:** none. **Used by:** pages.

### `CategoryBars`
One series of vertical bars with rounded tops, quiet grid lines and a tooltip. One colour, because the axis labels identify the bars.

### `PairedBars`
Two series measured in the same unit, side by side, with a legend. There is only ever one value axis.

### `TrendLine`
One series over a numeric axis, with a 2 px line and visible points.

### `ContributionBars`
Horizontal bars either side of a zero line. Red raises the score and blue lowers it, and the height grows with the number of rows.

### `StatTile`
A headline figure with a label and optional note.

## E. Classes Explained
None.

## F. Execution Flow
A page passes API values to a chart inside a `ChartCard`.

## G. Input and Output
Input: arrays of plain values. Output: SVG charts, or tables.

## H. Important Technical Concepts
- **No dual axes:** measures of different scale go in separate charts.
- **Tests read tables:** jsdom cannot lay charts out, so component tests use the table view, and browser tests check that real charts render.
- **CSP:** Recharts styles elements through the DOM, not inline style attributes, so the strict policy applies. The browser tests confirm it.

## I. Example
```tsx
<ChartCard title="Risk bands" tableColumns={columns} tableRows={rows}><CategoryBars data={risk} valueLabel="Transactions" /></ChartCard>
```

## J. Maintenance Notes
Add new chart types here, so pages keep using shared pieces.

## K. Related Files
- [chartColors.ts](../utils/chartColors.ts.explanation.md): colours.
- [DashboardPage.tsx](../pages/DashboardPage.tsx.explanation.md): main user.
