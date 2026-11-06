# tokens.css

Source: [frontend/src/styles/tokens.css](../../../../../frontend/src/styles/tokens.css)

## A. File Purpose
Defines the PRD 7.2 colour palette as CSS variables, plus base page styles and the temporary placeholder card style.

## B. Why This File Exists
With one definition of each colour, the consistent white theme required by PRD 7.1 is easy to keep and easy to change.

## C. Dependencies
- **Libraries:** none.
- **Internal modules:** none.
- **External services / database:** none.
- **Depended on by:** `main.tsx` loads it globally; `App.tsx` uses `setup-card`.

## D. Every Function Explained
CSS has no functions. The file has these rule blocks:
- `:root` holds the colour variables, `color-scheme: light` and the font stack.
- `body` applies the background and text colour.
- `.setup-card` and `.setup-card p` style the placeholder.
- A `max-width: 520px` media query gives the card a 16px phone gutter.

## E. Classes Explained
`.setup-card` is the only CSS class; it is temporary and is removed in Phase 4.

## F. Execution Flow
The browser applies these styles when `main.tsx` imports the file.

## G. Input and Output
Input: none. Output: variables available to all components.

## H. Important Technical Concepts
`color-scheme: light` tells the browser to draw native controls in light mode, matching the PRD's no-dark-theme rule. `#D97706` (warning) and `#DC2626` (danger) are reserved for status, and charts use separate colours.

| Variable | PRD colour |
|---|---|
| `--color-background` | Main background `#F8FAFC` |
| `--color-card` | Main card `#FFFFFF` |
| `--color-text` | Primary text `#172033` |
| `--color-text-secondary` | Secondary text `#64748B` |
| `--color-primary` | Primary blue `#2563EB` |
| `--color-primary-soft` | Secondary blue `#DBEAFE` |
| `--color-success` | Success `#16A34A` |
| `--color-warning` | Warning `#D97706` |
| `--color-danger` | Danger `#DC2626` |
| `--color-border` | Borders `#E2E8F0` |

## I. Example
```css
.card { background: var(--color-card); border: 1px solid var(--color-border); }
```

## J. Maintenance Notes
Change a colour only here. Component styles added in Phase 4 should use these variables rather than raw colour values.

## K. Related Files
- [main.tsx](../main.tsx.explanation.md): imports this file.
- [App.tsx](../App.tsx.explanation.md): uses the card style.
