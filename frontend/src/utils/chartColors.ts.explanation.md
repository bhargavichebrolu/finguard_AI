# chartColors.ts

Source: [frontend/src/utils/chartColors.ts](chartColors.ts)

## A. File Purpose
Holds the colours chart marks use: series colours, the raises and lowers pair for explanations, and recessive grid and axis colours.

## B. Why This File Exists
SVG presentation attributes cannot reliably read CSS variables, so charts need literal values. Keeping them in one file, each checked with the data-visualisation palette validator, stops colour choices spreading through components.

## C. Dependencies
- **Libraries:** none.
- **Internal modules:** none.
- **External services / database:** none.
- **Depended on by:** `components/charts.tsx`.

## D. Every Function Explained

No functions.

## E. Classes Explained
None.

## F. Execution Flow
Imported by chart components.

## G. Input and Output
Output: hex colour constants.

## H. Important Technical Concepts
- **Validated:** blue with amber, and red with blue, pass lightness, chroma, colour-blind separation, normal-vision separation and contrast checks.
- **Rejected palette:** green, amber and red for Low, Medium and High failed the normal-vision check (red and amber too similar), so the risk chart uses one colour and its axis labels identify each bar. Badges keep those colours because they always show the level in words.

## I. Example
```tsx
<Bar fill={SERIES_PRIMARY} />
```

## J. Maintenance Notes
Run the palette validator before adding a colour, and keep values within the PRD 7.2 palette or darker steps of it.

## K. Related Files
- [charts.tsx](../components/charts.tsx.explanation.md): uses these.
- [tokens.css](../../../docs/file-explanations/frontend/src/styles/tokens.css.explanation.md): the same values as CSS variables.
