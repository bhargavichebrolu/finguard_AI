# package.json

Source: [frontend/package.json](package.json)

## A. File Purpose
Declares the frontend's dependencies and its scripts.

## B. Why This File Exists
It is the single record of what the frontend needs. `package-lock.json` pins exact versions.

## C. Dependencies
- **Libraries:** npm.
- **Internal modules:** none.
- **External services / database:** the npm registry, when installing.
- **Depended on by:** developers, `npm ci`, and the scripts below.

## D. Every Function Explained

No functions.

## E. Classes Explained
None.

## F. Execution Flow
npm reads it for `install` and `run`.

## G. Input and Output
Scripts: `dev`, `build` (type check, then bundle), `preview` (serve the build with the Content Security Policy), `typecheck`, `test` (Vitest), `test:e2e` (Playwright) and `gen:api` (regenerate API types).

## H. Important Technical Concepts
- **Runtime dependencies are only the PRD 3.3 libraries:** React, React Router, Axios, Recharts and Lucide.
- **Development only:** Vitest, Testing Library, jsdom, Mock Service Worker, Playwright, axe, openapi-typescript and `@types/node`, as approved in the Phase 4 plan.
- **Vitest 5** is used because it is built for Vite 8. Vitest 3 brought its own older Vite, which broke type checking.

## I. Example
```powershell
npm ci
npm test
npm run build
```

## J. Maintenance Notes
Add a dependency in the same change as the code that first uses it, and run `npm audit`.

## K. Related Files
- [tsconfig.json](tsconfig.json.explanation.md): type checking.
- [vitest.config.ts](vitest.config.ts.explanation.md): unit tests.
