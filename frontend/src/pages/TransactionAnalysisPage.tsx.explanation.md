# TransactionAnalysisPage.tsx

Source: [frontend/src/pages/TransactionAnalysisPage.tsx](TransactionAnalysisPage.tsx)

## A. File Purpose
Page 2 of PRD 7.4, covering PRD 6.2: score one transaction and show the result and its explanation.

## B. Why This File Exists
PRD 6.2 defines the four inputs and forbids asking for post-transaction balances. The form asks for nothing else.

## C. Dependencies
- **Libraries:** React.
- **Internal modules:** components, `../services/api.ts`, `../services/endpoints.ts`.
- **External services / database:** `POST /api/v1/transactions/predict`.
- **Depended on by:** `registry.tsx`.

## D. Every Function Explained

### `validateForm`
Checks the amount (above 0, at most two decimals), the step (a whole number from 1 to 1,000,000) and the optional identifier (the API's pattern). Returns field messages.

### `destinationFor`
Returns `merchant` for PAYMENT and `customer` otherwise, the only combinations PaySim contains.

### `TransactionAnalysisPage`
Shows the form, the result or a prompt, and the explanation.

### `handleSubmit`
- **Purpose:** score.
- **Parameters / types:** the form event. **Returns / type:** `Promise<void>`.
- **Internal processing:** validates, then sends exactly amount, type, step and destination, plus the identifier if given. The amount is sent as typed text, so no decimal precision is lost.
- **Error handling:** field errors stop the request. API errors, such as a repeated identifier, show in an error state.
- **Calls:** `validateForm`, `transactionsApi.predict`. **Used by:** the form.

## E. Classes Explained
None.

## F. Execution Flow
Fill in, validate, send, then show the result.

## G. Input and Output
Input: four values and an optional identifier. Output: `PredictionResult` and `ExplanationPanel`.

## H. Important Technical Concepts
- **The destination select is disabled and explained,** rather than offering combinations the API would refuse.
- **Step help text** says only the hour of day reaches the model.

## I. Example
```ts
validateForm({ externalId: "", amount: "100.00", type: "TRANSFER", step: "5" }); // {}
```

## J. Maintenance Notes
Keep the client checks in step with `TransactionInput` in the API, which remains the authority.

## K. Related Files
- [PredictionResult.tsx](../components/PredictionResult.tsx.explanation.md): result.
- [transactions.py schemas](../../../backend/app/api/schemas/transactions.py.explanation.md): the API's rules.
