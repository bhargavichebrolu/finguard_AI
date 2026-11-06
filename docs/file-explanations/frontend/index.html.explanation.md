# index.html

Source: [frontend/index.html](../../../frontend/index.html)

## A. File Purpose
The single HTML page that loads the React application.

## B. Why This File Exists
A single-page application needs one document for the browser to open. Vite also uses this file as its bundling entry point.

## C. Dependencies
- **Libraries:** none directly.
- **Internal modules:** `/src/main.tsx`.
- **External services / database:** none.
- **Depended on by:** Vite.

## D. Every Function Explained
HTML has no functions. The file declares the language, character set, responsive viewport and title; a `#root` element for React; and a module script that loads `main.tsx`.

## E. Classes Explained
None.

## F. Execution Flow
The browser loads this page and runs the module script, and React then renders into `#root`.

## G. Input and Output
Input: a browser request. Output: an empty root element, filled by JavaScript.

## H. Important Technical Concepts
The viewport meta tag is required for the responsive layouts in PRD 7.3. From Phase 4, hosting must return this file for every route, so that React Router pages survive a refresh (PRD 11.2).

## I. Example
After `npm run build`, this file appears in `dist/index.html` with hashed asset names substituted.

## J. Maintenance Notes
Keep this file minimal. Page content belongs in React components.

## K. Related Files
- [main.tsx](src/main.tsx.explanation.md): loaded by this page.
- [vite.config.ts](vite.config.ts.explanation.md): build configuration.
