# AppLayout.tsx

Source: [frontend/src/layouts/AppLayout.tsx](AppLayout.tsx)

## A. File Purpose
The signed-in frame: top bar, collapsible left navigation, demo banner and content area.

## B. Why This File Exists
PRD 7.3 asks for a fixed or collapsible left navigation, a top bar and a main content area, responsive on mobile and desktop.

## C. Dependencies
- **Libraries:** React, React Router, `lucide-react`.
- **Internal modules:** `../hooks/useAuth.tsx`, `../pages/registry.tsx`, `../components/badges.tsx`, `../utils/format.ts`.
- **External services / database:** none.
- **Depended on by:** `App.tsx`.

## D. Every Function Explained

### `AppLayout`
- **Purpose:** render the frame around the current page.
- **Parameters / types:** none. **Returns / type:** a React element.
- **Internal processing:** lists navigation from `visiblePages(can)`, so each role sees only what it may use. On desktop the navigation collapses to icons. On narrow screens it becomes a panel opened from the menu button. It shows the email, role and a sign-out button, and for demo users a persistent banner.
- **Error handling:** none needed. **Calls:** `visiblePages`, `signOut`. **Used by:** the router.

### `onKey`
Nested in an effect that runs while the narrow-screen menu is open. Escape closes the menu and returns focus to the menu button.

## E. Classes Explained
None.

## F. Execution Flow
The router renders the layout, and the current page appears in `<Outlet />`.

## G. Input and Output
Output: header, navigation and main landmarks.

## H. Important Technical Concepts
- **Phones (M7 fix):** below 480 px the sign-out label is hidden visually but stays the button's accessible name, and the brand and role never wrap, so the top bar stays on one line at 390 px. The closed menu is `visibility: hidden`, so its links cannot take keyboard focus.
- **Skip link and landmarks:** a "Skip to content" link and labelled `nav` and `main` regions help keyboard and screen-reader users.
- **Research notice:** the top bar repeats that the data is synthetic and for demonstration.

## I. Example
```tsx
<Route element={<AppLayout />}>{/* pages */}</Route>
```

## J. Maintenance Notes
Navigation order follows `PAGES` in `registry.tsx`, which follows PRD 7.4.

## K. Related Files
- [registry.tsx](../pages/registry.tsx.explanation.md): the page list.
- [layout.css](../styles/layout.css.explanation.md): styles.
