# App.tsx

Source: [frontend/src/App.tsx](../../../../frontend/src/App.tsx)

## A. File Purpose
The root React component. For now it is a placeholder confirming that the frontend toolchain works.

## B. Why This File Exists
Phase 1 needs a working frontend environment, so that a type check and production build can be verified. It shows no statistics, because no real data is connected yet and the PRD forbids fake figures.

## C. Dependencies
- **Libraries:** React, through the JSX runtime.
- **Internal modules:** none. Styling comes from `tokens.css`, which `main.tsx` loads.
- **External services / database:** none.
- **Depended on by:** `main.tsx`.

## D. Every Function Explained

### `App`
- **Purpose:** render the placeholder card.
- **Parameters / types:** none.
- **Returns / type:** `JSX.Element`.
- **Internal processing:** static markup only.
- **Error handling:** none needed.
- **Calls:** nothing.
- **Used by:** `main.tsx`.

## E. Classes Explained
None.

## F. Execution Flow
React calls `App` once and displays the returned markup.

## G. Input and Output
No input. The output is a heading and a one-line status message.

## H. Important Technical Concepts
The component uses the `setup-card` class rather than inline colours, so the PRD's palette tokens stay in one place.

## I. Example
```tsx
<App />
```

## J. Maintenance Notes
Phase 4 replaces this with routing and the application layout, and removes `setup-card` from `tokens.css`.

## K. Related Files
- [main.tsx](main.tsx.explanation.md): renders this component.
- [tokens.css](styles/tokens.css.explanation.md): styles.
