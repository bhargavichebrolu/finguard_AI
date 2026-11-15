# tsconfig.json

Source: [frontend/tsconfig.json](tsconfig.json)

## A. File Purpose
TypeScript settings for the application, tests and config files.

## B. Why This File Exists
Strict type checking catches mistakes against the generated API types before they reach the browser.

## C. Dependencies
- **Libraries:** TypeScript.
- **Internal modules:** `src`, `tests` and the config files are included.
- **External services / database:** none.
- **Depended on by:** `npm run build`, `npm run typecheck`, editors.

## D. Every Function Explained

No functions.

## E. Classes Explained
None.

## F. Execution Flow
Read by `tsc --noEmit` before every build.

## G. Input and Output
Output: type errors, or none.

## H. Important Technical Concepts
- **`playwright.prodlike.config.ts`** is type-checked too (Phase 5 M5).
- **`playwright.perf.config.ts`** is type-checked too (Phase 5 M2).
- **`strict`, `noUnusedLocals`, `noUnusedParameters`** stay on.
- **`types`:** `vite/client` for `import.meta.env`, and `node` for the config files.

## I. Example
```powershell
npm run typecheck
```

## J. Maintenance Notes
Do not relax strictness to silence an error.

## K. Related Files
- [package.json](package.json.explanation.md): scripts.
