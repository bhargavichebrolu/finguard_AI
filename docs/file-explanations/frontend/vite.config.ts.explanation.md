# vite.config.ts

Source: [frontend/vite.config.ts](../../../frontend/vite.config.ts)

## A. File Purpose
Configures Vite, the frontend's development server and production bundler.

## B. Why This File Exists
Vite needs the React plugin to compile JSX, and a fixed port keeps the local CORS configuration predictable.

## C. Dependencies
- **Libraries:** `vite`, `@vitejs/plugin-react`.
- **Internal modules / external services / database:** none.
- **Depended on by:** `npm run dev`, `npm run build`, `npm run preview`.

## D. Every Function Explained
This file defines no named functions. It calls `defineConfig`, a typing helper from Vite, and `react()`, which creates the plugin. Vite imports the default export.

## E. Classes Explained
None.

## F. Execution Flow
Vite loads this file at startup, applies the plugin and starts the dev server on port 5173, or bundles into `dist/`.

## G. Input and Output
Input: none at runtime. Output: a Vite configuration object.

## H. Important Technical Concepts
No API proxy or URL is configured here on purpose. From Phase 4, the API base URL comes from `VITE_API_BASE_URL`, as PRD 11.2 forbids a hardcoded localhost URL in production.

## I. Example
```powershell
cd frontend; npm run dev
```

## J. Maintenance Notes
If the port changes, update `CORS_ALLOWED_ORIGINS` in `.env.example`. Test configuration is expected to be added here in Phase 4.

## K. Related Files
- [index.html](index.html.explanation.md): Vite's entry point.
- [main.tsx](src/main.tsx.explanation.md): application entry.
