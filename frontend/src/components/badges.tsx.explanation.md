# badges.tsx

Source: [frontend/src/components/badges.tsx](badges.tsx)

## A. File Purpose
Small labels for risk level, model decision, workflow status and demo records.

## B. Why This File Exists
Risk, decision and status must be recognisable at a glance, without relying on colour alone (accessibility), and in words that do not claim fraud.

## C. Dependencies
- **Libraries:** React.
- **Internal modules:** `../utils/format.ts`.
- **External services / database:** none.
- **Depended on by:** tables and detail views.

## D. Every Function Explained

### `RiskBadge`
Shows "Low risk", "Medium risk" or "High risk" with a tooltip giving the band's rule, for example that Low means below the frozen threshold.

### `DecisionBadge`
Shows "Flagged for review" or "Not flagged".

### `StatusBadge`
Shows a workflow status such as "Under review", or a dash.

### `DemoBadge`
Shows "Synthetic demo record" (PRD 7.6).

## E. Classes Explained
None.

## F. Execution Flow
Rendered inside tables and detail panels.

## G. Input and Output
Input: API values. Output: a labelled `<span>`.

## H. Important Technical Concepts
- **Text first, colour second:** every badge reads correctly in greyscale. The colours use darker text tokens for contrast.

## I. Example
```tsx
<RiskBadge level="HIGH" />
```

## J. Maintenance Notes
A new risk level needs a class here, and the matching style.

## K. Related Files
- [format.ts](../utils/format.ts.explanation.md): wording.
- [components.css](../styles/components.css.explanation.md): colours.
