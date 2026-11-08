# layout.css

Source: [frontend/src/styles/layout.css](layout.css)

## A. File Purpose
Styles the application frame: top bar, navigation, demo banner and content area, including the mobile layout.

## B. Why This File Exists
PRD 3.3 asks for custom CSS and no UI framework, and PRD 7 asks for a consistent white theme. A few global stylesheets keep that consistent and keep documentation proportionate.

## C. Dependencies
- **Libraries:** none.
- **Internal modules:** the variables in `tokens.css`.
- **External services / database:** none.
- **Depended on by:** `main.tsx` imports it.

## D. Every Function Explained

No functions.

## E. Classes Explained
None.

## F. Execution Flow
Loaded once by `main.tsx`.

## G. Input and Output
Output: style rules.

## H. Important Technical Concepts
- **Tokens only:** colours come from `tokens.css` variables, never raw values, except white on primary buttons.
- Below 900 px the navigation becomes a panel opened from the menu button, and the content uses the full width, so nothing scrolls sideways.
- **No inline styles:** the Content Security Policy forbids inline style attributes, so all styling lives in these files.

## I. Example
```css
.card { border-radius: var(--radius); }
```

## J. Maintenance Notes
Prefer reusing an existing class to adding a new one.

## K. Related Files
- [tokens.css](../../../docs/file-explanations/frontend/src/styles/tokens.css.explanation.md): the variables.
- [main.tsx](../../../docs/file-explanations/frontend/src/main.tsx.explanation.md): imports these.
