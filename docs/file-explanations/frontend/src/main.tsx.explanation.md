# main.tsx

Source: [frontend/src/main.tsx](../../../../frontend/src/main.tsx)

## A. File Purpose
The browser entry point. It loads the stylesheets and mounts the application.

## B. Why This File Exists
Vite starts from this file, which `index.html` loads.

## C. Dependencies
- **Libraries:** React, React DOM.
- **Internal modules:** `App.tsx`, and the four stylesheets in `styles/`.
- **External services / database:** none.
- **Depended on by:** `index.html`.

## D. Every Function Explained
No named functions. The module finds `#root` and renders `<App />` inside `StrictMode`.

## E. Classes Explained
None.

## F. Execution Flow
Import the styles, find the root element, render.

## G. Input and Output
Input: `index.html`. Output: the running application.

## H. Important Technical Concepts
- **Fails loudly:** a missing `#root` throws a clear error instead of rendering nothing.
- **`StrictMode`** runs extra development checks.

## I. Example
```html
<script type="module" src="/src/main.tsx"></script>
```

## J. Maintenance Notes
New global stylesheets are imported here, after `tokens.css`.

## K. Related Files
- [App.tsx](App.tsx.explanation.md): the root component.
- [tokens.css](styles/tokens.css.explanation.md): design tokens.
