# InvestigationCentrePage.tsx

Source: [frontend/src/pages/InvestigationCentrePage.tsx](InvestigationCentrePage.tsx)

## A. File Purpose
Page 5 of PRD 7.4, covering PRD 6.7: the review queue, each case's status history and notes, and status, assignment and note actions for investigators and administrators.

## B. Why This File Exists
PRD 6.7 requires status updates, notes and a history of changes, and states that statuses are workflow labels, not verified findings. PRD 7.5 requires confirmation of significant actions.

## C. Dependencies
- **Libraries:** React, React Router.
- **Internal modules:** components, `../hooks`, `../services/api.ts`, `../services/endpoints.ts`, `../utils/format.ts`.
- **External services / database:** `GET /investigations`, `GET`, `PATCH /investigations/{id}`, `POST /investigations/{id}/notes`, `GET /users/assignable`.
- **Depended on by:** `registry.tsx`.

## D. Every Function Explained

### `InvestigationCentrePage`
Shows the status filter, an "Assigned to me" filter and the paged queue. The open case lives in the address as `?open=<id>`, so the explorer can link straight to it.

### `open`
Sets or clears `?open=` in the address.

### `InvestigationPanel`
- **Purpose:** show one case.
- **Parameters / types:** `id`, `summary`, `onClose`, `onChanged`. **Returns / type:** a labelled region.
- **Internal processing:** shows status, model decision and score, dates, status history and notes. Users with `update_investigations` get the status, assignee and note controls. Others get a read-only notice.
- **Error handling:** refusals from the API show in an error state. **Calls:** `act`. **Used by:** the page.

### `act`
Nested in `InvestigationPanel`. Runs a change, then reloads the case and the queue, or shows the error.

### `StatusControl`
A status select and an Update button. Choosing `CLOSED` or `FALSE_ALARM` opens a confirmation explaining that this records a workflow outcome and changes no score or decision.

### `submit`
Two nested handlers: in `StatusControl` it applies the status or asks for confirmation, and in `NoteForm` it sends the trimmed note and clears the box.

### `AssigneeControl`
Shows who the case is assigned to. A select lists the restricted assignee list (active investigators and administrators), with "Assign to me" and "Nobody".

### `NoteForm`
A text box up to 5,000 characters with a counter. Blank notes cannot be sent.

### `error`
Inside `act`: the failure as an `ApiError`; a 409 also reloads the case.

## E. Classes Explained
None.

## F. Execution Flow
Filter the queue, open a case, act, then the case and queue reload.

## G. Input and Output
Input: filters and actions. Output: the queue and the case panel.

## H. Important Technical Concepts
- **Stale status (Phase 5 M7):** a status change sends `expected_status`, the status shown. If a colleague changed it first, the API answers 409; `act` shows the message and reloads the case and the queue, so the reviewer sees the current status before deciding again.
- **`CONCLUDING`** holds the statuses that ask for confirmation. Any status can still follow any other, as the API allows, and the history records each move.
- **`STATUSES`** is the PRD 6.7 list, in order.
- **Accessible names:** an earlier version labelled the forms with the same words as their fields, giving two controls one name. The form labels were removed.

## I. Example
```tsx
<Link to={`/investigations?open=${id}`}>Open in the Investigation Centre</Link>
```

## J. Maintenance Notes
Keep the workflow statement visible on the queue and on each case.

## K. Related Files
- [investigation_service.py](../../../backend/app/services/investigation_service.py.explanation.md): the rules.
- [feedback.tsx](../components/feedback.tsx.explanation.md): the confirmation dialog.
