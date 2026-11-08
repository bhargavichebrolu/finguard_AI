# tokens.css

Source: [frontend/src/styles/tokens.css](../../../../../frontend/src/styles/tokens.css)

## A. File Purpose
Defines the design tokens: PRD 7.2 colours, darker text steps for contrast, radii, shadow, spacing and layout sizes. Also the base page styles.

## B. Why This File Exists
PRD 7.2 fixes the palette, and PRD 7.1 requires a consistent white theme. Components use these variables, never raw colours.

## C. Dependencies
- **Libraries:** none.
- **Internal modules:** none.
- **External services / database:** none.
- **Depended on by:** every other stylesheet.

## D. Every Function Explained
No functions.

## E. Classes Explained
None.

## F. Execution Flow
Loaded first by `main.tsx`.

## G. Input and Output
Output: CSS custom properties on `:root`.

## H. Important Technical Concepts
- **Contrast:** the PRD's success, warning and danger colours are too light for small text on tinted backgrounds, so darker text tokens of the same hues (`--color-*-text`) are used for badge text.
- **`color-scheme: light`:** the PRD forbids a dark theme.
- **Reduced motion:** animations stop when the reader asks for less motion.

## I. Example
```css
.badge-high { color: var(--color-danger-text); }
```

## J. Maintenance Notes
Change PRD colours only if the PRD changes. Add new tokens here, rather than raw values in other files.

## K. Related Files
- [components.css](../../../../../frontend/src/styles/components.css.explanation.md): uses the tokens.
