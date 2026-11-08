# TransactionDetailPanel.tsx

Source: [frontend/src/components/TransactionDetailPanel.tsx](TransactionDetailPanel.tsx)

## A. File Purpose
Shows everything PRD 6.6 lists for one transaction: attributes, score, model version, timestamp, explanation, investigation status, notes and status history.

## B. Why This File Exists
The explorer and other pages need one consistent detail view.

## C. Dependencies
- **Libraries:** React, React Router.
- **Internal modules:** `PredictionResult.tsx`, `ExplanationPanel.tsx`, `badges.tsx`, `feedback.tsx`, `../hooks/useApiResource.ts`.
- **External services / database:** `GET /api/v1/transactions/{id}`.
- **Depended on by:** the Transaction Explorer.

## D. Every Function Explained

### `TransactionDetailPanel`
- **Purpose:** load and show one transaction.
- **Parameters / types:** `transactionId`, `onClose`. **Returns / type:** a labelled region.
- **Internal processing:** shows the prediction, then the investigation with its status, a timeline of status changes and the notes, then the explanation. It links to the Investigation Centre for changes.
- **Error handling:** loading and error states. When there is no investigation it explains when one is opened. **Calls:** `transactionsApi.get`. **Used by:** the explorer.

## E. Classes Explained
None.

## F. Execution Flow
Loads when opened, and closes on request.

## G. Input and Output
Output: a region labelled "Transaction detail".

## H. Important Technical Concepts
- **Read-only here:** changing status or adding notes happens in the Investigation Centre, where the permission checks and confirmations live.

## I. Example
```tsx
<TransactionDetailPanel transactionId={id} onClose={() => setSelected(null)} />
```

## J. Maintenance Notes
Keep the workflow statement beside the status.

## K. Related Files
- [TransactionExplorerPage.tsx](../pages/TransactionExplorerPage.tsx.explanation.md): opens this.
- [PredictionResult.tsx](PredictionResult.tsx.explanation.md): the score view.
