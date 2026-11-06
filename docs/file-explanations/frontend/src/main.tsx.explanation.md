# main.tsx

Source: [frontend/src/main.tsx](../../../../frontend/src/main.tsx)

## A. File Purpose
Mounts the React application into the page and loads the global design tokens.

## B. Why This File Exists
It separates the one-time browser setup from the application component, so `App` can be rendered by tests without a real page.

## C. Dependencies
- **Libraries:** `react` (`StrictMode`), `react-dom/client` (`createRoot`).
- **Internal modules:** `./App`, `./styles/tokens.css`.
- **External services / database:** none.
- **Depended on by:** `frontend/index.html`.

## D. Every Function Explained
This file defines no functions. It runs three top-level steps: find `#root`, throw an `Error` if it is missing, and render `App` inside `StrictMode`.

## E. Classes Explained
None.

## F. Execution Flow
Module imports run first, which also applies the CSS. Then React renders `App` into the root element.

## G. Input and Output
Input: the `#root` element from `index.html`. Output: the rendered application.

## H. Important Technical Concepts
`StrictMode` runs extra development-only checks to surface side-effect bugs early; it has no effect on production behaviour. The explicit null check gives a clear message and satisfies TypeScript's strict mode without a non-null assertion.

## I. Example
There is nothing to call: the browser runs this file when the page loads.

## J. Maintenance Notes
From Phase 4, app-wide providers such as the router can wrap `App` here, or inside `App`.

## K. Related Files
- [App.tsx](App.tsx.explanation.md): root component.
- [tokens.css](styles/tokens.css.explanation.md): design tokens.
- [index.html](../index.html.explanation.md): loads this file.
