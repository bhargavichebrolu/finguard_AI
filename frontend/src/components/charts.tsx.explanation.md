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

### `legendText`
Renders a legend label in text ink through the `chart-legend-text` class, so the coloured marker alone carries series identity.

### `CategoryBars`
One series of vertical bars with rounded tops, quiet grid lines and a tooltip. One colour, because the axis labels identify the bars. Optional `format` formats the axis and tooltip for measures with decimals, such as PR-AUC; counts are the default and allow no decimals.

### `PairedBars`
Two series measured in the same unit, side by side, with a legend. There is only ever one value axis.

### `TrendLine`
One series over a numeric axis, with a 2 px line and visible points.

### `ContributionBars`
Horizontal bars either side of a zero line. Red raises the score and blue lowers it, and the height grows with the number of rows.

### `StatTile`
A headline figure with a label and optional note.

### `CurveChart`
- **Purpose:** draw up to two curves on numeric axes, such as precision against recall or ROC.
- **Parameters / types:** `series: CurveSeries[]`, `xLabel`, `yLabel`, `logX` (default false). **Returns / type:** a line chart.
- **Internal processing:** each series carries its own points. Both axes run from 0 to 1, unless `logX` puts the x axis on a log scale for thresholds. Only the first two series are drawn.
- **Error handling:** none. **Calls:** Recharts. **Used by:** `ModelPerformancePage.tsx`.

## E. Classes Explained
None.

## F. Execution Flow
A page passes API values to a chart inside a `ChartCard`.

## G. Input and Output
Input: arrays of plain values. Output: SVG charts, or tables.

## H. Important Technical Concepts
- **Fixed ticks:** `CurveChart` uses ticks at 0, 0.2 ... 1 and powers of ten on the log axis, because automatic ticks such as 0.25 printed to one decimal place as a misleading 0.3. The legend sits above the plot so it cannot collide with the x axis title.
- **`formatValue`** is a local value in `CategoryBars`, not a function: the chosen formatter.
- **`CurveSeries`** is an interface: a name and its points. `CurveChart` draws at most two, because only the primary and secondary colours passed the palette check together.
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
