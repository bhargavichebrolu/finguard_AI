# render.tsx

Source: [frontend/tests/unit/render.tsx](render.tsx)

## A. File Purpose
Renders the real application routes at a chosen address, with the real providers.

## B. Why This File Exists
Testing pages through the real routes and guards, instead of in isolation, catches wiring mistakes such as a missing permission.

## C. Dependencies
- **Libraries:** Testing Library, React Router.
- **Internal modules:** `../../src/App.tsx` (`AppRoutes`), `../../src/hooks/useAuth.tsx`.
- **External services / database:** none. The mock API answers.
- **Depended on by:** page tests.

## D. Every Function Explained

### `renderApp`
Renders `AppRoutes` inside `AuthProvider` and a memory router starting at `path`.

## E. Classes Explained
None.

## F. Execution Flow
A test calls `renderApp("/system")`, then queries the screen.

## G. Input and Output
Output: Testing Library's render result.

## H. Important Technical Concepts
- **Memory router:** addresses change without a browser.

## I. Example
```ts
renderApp("/system");
```

## J. Maintenance Notes
Add any new top-level provider here as well as in `App.tsx`.

## K. Related Files
- [auth.test.tsx](auth.test.tsx.explanation.md): uses this.
