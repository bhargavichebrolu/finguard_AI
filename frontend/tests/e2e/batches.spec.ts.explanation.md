# batches.spec.ts

Source: [frontend/tests/e2e/batches.spec.ts](batches.spec.ts)

## A. File Purpose
Tests CSV batches end to end: file checks, column refusals, progress, row-level errors, paged results and spreadsheet-safe downloads.

## B. Why This File Exists
PRD 6.3 and the Phase 4 brief require upload validation, progress, row errors, error reports, paging and safe exports.

## C. Dependencies
- **Libraries:** Playwright Test.
- **Internal modules:** `support.ts`.
- **External services / database:** The browser-test API on 127.0.0.1:8011 and the finguard_e2e_test database, through the preview server on 127.0.0.1:4173.
- **Depended on by:** none; run by `npm run test:e2e`.

## D. Every Function Explained

### `csvFile`
Builds an in-memory file for `setInputFiles`.

### `goodRows`
Builds valid rows with unique identifiers.

### `cells`
Splits a CSV line, honouring quotes.

### `download`
Clicks a download button and returns the file name and lines.

### `expectSpreadsheetSafe`
Fails if any exported cell begins with =, +, -, @, tab or carriage return without a neutralising quote.

### `upload`
Chooses a file and clicks Upload and score.

### `scores`
A local value, not a function: the score column of the first results page.

### `job`
A local value, not a function: the most recent job read back after the resume test.

### `snapshot`
Inside the progress test's poll: the bar's value and the status word before the colon in its label (for example Processing or Completed), read together in one `evaluate` call from the same render. The poll ends when the label reads Completed.

### `second`
In the duplicate-file test: the second job's counts, which must show nothing stored and every row failed.

### `stored`
In the duplicate-file test: how many transactions carry the first row's identifier (must be one).

## E. Classes Explained
None.

## F. Execution Flow
Each test signs in through a saved state and works through the real interface and API.

## G. Input and Output
| Test | Proves |
|---|---|
| checks the file before uploading | Wrong type and empty file messages; upload disabled. |
| refuses columns that are not available when a transaction is scored | Balance columns refused; missing columns named. |
| scores good rows, reports bad rows, pages results and exports safely | 60 stored, 3 refused (two shaped like formulas), labels ignored and stored apart, results sorted and paged 25 at a time, results and error CSVs with exact headers, no labels in exports, no formula cells. |
| shows processing progress for a larger file until it completes | 20,000 rows: progress seen before completion and never going backwards. |
| resumes a batch after the API restarts mid-job, storing every row once | Phase 5 M4: a graceful container restart mid-job; the page shows the resume, and all 20,000 rows are stored once, on attempt 2. |

## H. Important Technical Concepts
- **Database outage and duplicates (Phase 5 M7):** one test switches the database off mid-job: the page says it lost contact, and the job resumes (attempt 2) and completes with every row once, never failed. Another submits the same file twice: the second job stores nothing and reports every row as already existing.
- **Progress polled to completion (Phase 5 M6):** the progress test polls until the status label reads Completed, not until the bar reads 100. The last chunk is stored (100%) a moment before the job is marked completed, so stopping at 100 made the check that the label changed depend on timing; it failed once in WebKit.
- **Bar and label read together (Phase 5 gate investigation):** the poll used to read the bar's value, then the label, in two separate browser calls. A re-render could fall between them: the bar was read at 95 while Processing, the next API answer brought Completed at 100, and the label was then read as Completed. The poll ended with 95 as the last value, and `seen[seen.length - 1]` failed although the page never showed Completed beside 95. Traces of the two failures (Firefox, 2 of 13 investigation runs) show the API going from Processing at 95% straight to Completed at 100%; it never reported Completed below 100. Both are now read in one `evaluate` call, which sees one render. Every assertion is unchanged.
- **Formula safety:** the error report records the row, column and message, never the submitted text, so formula-shaped input cannot reach a spreadsheet; the check covers every exported cell anyway.

## I. Example
```powershell
npm run test:e2e -- tests/e2e/batches.spec.ts --project=setup --project=desktop
```

## J. Maintenance Notes
Keep the bad rows at the end so their row numbers stay 62 to 64.

## K. Related Files
- [support.ts](support.ts.explanation.md): shared helpers.
- [batch_service.py](../../../backend/app/services/batch_service.py.explanation.md): processing.
