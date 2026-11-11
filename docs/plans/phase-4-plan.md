# Phase 4 plan: React frontend

**Status: approved and implemented; Phase 4 was accepted and merged into `main` at `5c392a5` on 2026-11-08 ([phase-4-completion.md](phase-4-completion.md)).** The text below is the plan as proposed. When it was written, no frontend code existed. This plan answers the items raised at the Phase 3 gate. The decisions marked **Decision needed** are for the reviewer.

## 1. Constraints carried into Phase 4

- The frozen model, its threshold and all Phase 1 and 2 outputs stay unchanged. Nothing is retrained, and the test partition is not read.
- `model_score` is never presented as a probability or percentage chance, and `FLAG_FOR_REVIEW` is never presented as a fraud finding.
- The measured limitations are disclosed in the interface, from saved results, not typed in: test FPR 0.282% against the 0.1% target, recall 45.9% overall and 21.9% in normal steps.
- No statistic is hardcoded (PRD 7.5). Every figure comes from the API.
- White theme and PRD 7.2 colours, with custom CSS. Uses the PRD 3.3 libraries, already installed: React, TypeScript, Vite, Recharts, React Router, Axios and Lucide.
- Every authored file gets a sibling explanation document. `PROJECT_CONNECTIONS.md` is updated as pages land.

## 2. Frontend architecture

```
frontend/src/
  main.tsx, App.tsx          router, providers
  services/api.ts            one Axios instance: base URL from VITE_API_BASE_URL, bearer token,
                             error normalisation (detail, request_id), 401 handling
  services/*.ts              one module per API area: auth, transactions, batches,
                             investigations, models, reports, settings, system, users
  types/api.generated.ts     generated from /openapi.json, committed, never edited
  types/*.ts                 hand-written view types where a page needs them
  hooks/                     useAuth, useApiResource (load, error, retry), usePolling, useDownload
  layouts/AppLayout.tsx      collapsible left navigation, top bar, content area
  components/                shared pieces: ScoreDisclosure, RiskBadge, DecisionBadge, DataTable,
                             EmptyState, ErrorState, LoadingState, ConfirmDialog, StatTile, charts
  pages/                     the ten PRD 7.4 pages, plus Login
  styles/                    tokens.css, plus a few global stylesheets
  utils/                     formatting
```

- **Types follow the API automatically.** `openapi-typescript` turns the backend's schema into TypeScript types, run by `npm run gen:api`. A test fails if the committed file differs from a fresh generation, so a backend change cannot silently break the frontend. The generated file is exempt from the explanation rule as generated output (PRD 12.2), and the checker gets a documented exemption list.
- **Data fetching uses small custom hooks** rather than a new data library, keeping to the PRD's list. Each hook exposes loading, error and data, so every page shows the PRD 7.5 states the same way.
- **Styling uses a few global stylesheets** (`tokens.css`, `layout.css`, `components.css`, `pages.css`) rather than one per component. That keeps the explanation workload proportionate, because the checker covers `.css` files.
- **Charts** use Recharts with the PRD colours. Identity never depends on colour alone: risk bands always carry text labels, and every chart has a table view.

### Pages and their data

| PRD 7.4 page | API sources | Notes |
|---|---|---|
| Login | `POST /auth/login`, `GET /auth/me` | No self-registration |
| 1. Dashboard | `GET /reports/summary`, `GET /models/metrics` | Model flags, investigation workflow and uploaded labels as three visually separate sections (PRD 6.1) |
| 2. Transaction Analysis | `POST /transactions/predict` | Four inputs, merchant only with PAYMENT enforced in the form, result card with explanation |
| 3. CSV Batch Analysis | `POST /batches/upload`, `GET /batches/{id}`, `/results`, `/export`, `/errors`, `GET /settings` | See section 6 |
| 4. Transaction Explorer | `GET /transactions`, `GET /transactions/{id}` | Every PRD 6.5 filter, sorting, paging, detail panel |
| 5. Investigation Centre | `GET`, `PATCH /investigations`, `POST .../notes` | See section 7 |
| 6. Model Performance | `GET /models/metrics`, and a new `GET /models/report` | See section 8 |
| 7. Explainable AI | `GET /models/feature-importance`, transaction detail | Global importance by group and feature, a local explanation viewer, limitations always shown |
| 8. Reports | `GET /reports/export?report_type=` | Four downloads |
| 9. Settings | `GET`, `PATCH /settings`, admin user management | Threshold shown read-only with the reason |
| 10. System Information | `GET /system/status`, `GET /health`, `GET /audit-logs` (admin) | Model hash, versions, database state |

## 3. Score presentation and limitation disclosure

| Item | How it is shown |
|---|---|
| `model_score` | "Model score (uncalibrated)", to four decimal places, for example 0.8377. Never with `%`. |
| `risk_score` | "Risk score 83.8 (score × 100, not a percentage)" |
| Decision | "Flagged for review" or "Not flagged", with a short explanation of what a flag means |
| Risk level | Low, Medium or High badge, with text and colour, and a tooltip giving the band rule |
| `ScoreDisclosure` | On Dashboard, Transaction Analysis, Batch results, Explorer detail and Model Performance. It shows the `performance_notes` returned by `/models/metrics`, so the 0.282%, 45.9% and 21.9% figures come from the saved file. If they cannot load, it says so in a warning and does not show the score as if nothing were missing. |
| Explanations | Labelled "how the model reacted to this input, not what causes fraud", with the saved limitations |
| Demo mode | A persistent "Demo mode: synthetic sample records" banner for the demo role, and demo statistics labelled as such (PRD 7.6) |

**Guard tests:**
- No user-facing string in `src/` contains "probability", "% chance", "fraud detected" or "confirmed fraud", except in the disclosure that says the score is not a probability.
- No numeric literal matching a saved metric appears in `src/`.
- The disclosure renders the API's figures.

## 4. Authentication and token handling

- Login form posts to `/auth/login`, then `GET /auth/me` loads the account and its permissions.
- `RequireAuth` and `RequirePermission` route guards. Navigation hides pages a role cannot use, and buttons for actions it cannot take. The server stays the authority: the interface only mirrors it, and a 403 is still handled.
- A 401 from any request clears the session and returns to login with a message. The 30-minute expiry is handled the same way.
- Logout clears the session. A password change signs out other sessions, as the backend already does.

**Decision needed: where the token lives.**

| Option | Security | Effort | Experience |
|---|---|---|---|
| **A. In memory only (recommended for Phase 4)** | Not readable after the page closes. An XSS bug could still use it while the page is open, which the CSP in section 9 reduces. | Frontend only | Sign in again after a reload, or after 30 minutes |
| B. HttpOnly refresh cookie plus in-memory access token | Script cannot read the refresh token at all | Backend changes: refresh endpoint, cookie, CSRF protection, credentialed CORS | Stays signed in across reloads |
| C. `localStorage` | Any XSS can read it | Least | Stays signed in |

Option C is not recommended. Option B can follow in Phase 5 or 6 if reload sign-in proves annoying.

## 5. Dashboard (PRD 6.1)

- **Model flags:** stat tiles for analysed, flagged for review, flag rate and total value. Also a risk distribution bar, flags by transaction type, and flags per simulated day as a line chart.
- **Investigation workflow:** status counts.
- **Uploaded labels:** labelled rows and labelled fraud value, shown only when labels exist, with the note that they were not used for scoring.
- **Model performance summary:** headline saved figures plus `ScoreDisclosure`, linking to Model Performance.
- **Recent activity:** the five newest predictions.
- Wording throughout says "flagged" rather than "fraudulent predictions", and "flag rate" rather than "fraud rate", because PRD 6.1's terms would misstate what the numbers are.

## 6. CSV batches

1. Before upload, the page reads limits from `GET /settings` and checks extension and size in the browser. The server checks everything again.
2. Upload progress uses Axios `onUploadProgress`, then processing progress comes from polling `GET /batches/{id}` every second, slowing after 30 seconds, until the job finishes.
3. Results show succeeded, failed and total counts, ignored columns (such as `isFraud`) with the reason, and a paged results table.
4. The error report and results export download through the authenticated client, saved as files.
5. A `FAILED` job shows the server's message and suggests uploading again.
6. A downloadable template CSV with the required columns.

## 7. Investigation Centre

- **Queue:** status and assignee filters, and score and risk columns, with the standing workflow note.
- **Detail panel:** transaction, score, explanation, a status history timeline and notes.
- **Actions** (investigator and admin only): change status, add a note, assign to me or unassign. Changing to `CLOSED` or `FALSE_ALARM` asks for confirmation (PRD 7.5).
- **Assignment needs a backend addition.** Only admins can list users today, so investigators cannot pick an assignee. Proposed: `GET /api/v1/users/assignable`, which returns the ID and email of active investigators and admins, for roles that can update investigations.
- Analysts see the same pages read-only, and demo users do not see the page.

## 8. Model performance without retraining or test access

**The data already exists.** The saved Phase 2 outputs hold everything PRD 6.8 asks for:

| PRD 6.8 item | Saved source |
|---|---|
| Model comparison table | `selection.json` (best per family, intervals, gates), `all_runs.csv` |
| Metric comparison charts | `all_runs.csv`, imbalance matrix |
| PR and ROC curves | `selection.json` `candidate_curves` (validation), `test_evaluation.json` `curves` (test, about 200 points each) |
| Confusion matrices | `model_v1_metrics.json` (validation and test) |
| Threshold comparison | `threshold_analysis.json` (sweep, PRD candidates, rule alternatives, out-of-bag) |
| Training and inference time | `all_runs.csv` |
| Feature importance | `model_v1_metrics.json`, `shap_summary.json` |
| Experiment history | `all_runs.csv` (125 runs, with stage and status) |

**Proposed approach (recommended):**
1. A new script, `scripts/export_model_report.py`, reads only those saved files and writes one new file, `artifacts/metadata/model_v1_report.json`. No existing file is changed.
2. The API checks the report's hash at start-up, as it does for the other metadata, and serves it read-only at `GET /api/v1/models/report`.
3. The frontend draws its own charts from it with Recharts. Charts can be read with a screen reader, have table views, and follow the theme, which the PNGs in `experiments/figures/` do not.

**Guards:**
- A test proves every value in the report equals its source value.
- A source scan proves the script imports neither the partition loaders nor `final_evaluation`, and opens nothing under `data/`.
- The script fails if any source hash differs from the committed one.

**Presentation rules:**
- Test figures are labelled "test partition, evaluated once after the freeze".
- Validation figures are labelled as the basis for selection.
- Test's higher precision and PR-AUC are explained as partly reflecting its higher fraud rate.
- The LightGBM rows are marked as a numerical divergence, as `ML_EXPERIMENTS.md` describes.
- The three-way tie at the top is stated rather than implying XGBoost won.

The alternative, the frontend importing the JSON files at build time, needs no backend change. But it ties the frontend build to the `experiments/` folder, which the deployed frontend should not need.

## 9. Security gaps from Phase 3

| Gap | Plan |
|---|---|
| No Content Security Policy (frontend) | Policy: `default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self' <API origin>; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'`. Set on `vite preview` in Phase 4 and checked by the end-to-end tests, which fail on any CSP violation in the console. Host header files move to Phase 6 once a host is chosen. No inline scripts or `style` attributes in HTML. React sets styles through the DOM, which this policy allows, and the tests confirm it. |
| No CSP on the API | API responses get `default-src 'none'; frame-ancestors 'none'`. `/docs` gets its own policy allowing the Swagger UI CDN and its inline start-up script, since the PRD requires Swagger. |
| Client address behind a proxy | A `TRUSTED_PROXY_IPS` setting, empty by default, passed to Uvicorn's `--forwarded-allow-ips` with `--proxy-headers`. Forwarded headers are honoured only from those addresses. Tests prove a spoofed `X-Forwarded-For` from an untrusted client does not change the rate-limit key. The real value is set in Phase 6. |
| Tokens and XSS | Token in memory (section 4), the CSP above, no `dangerouslySetInnerHTML`, and a lint rule enforcing that. |
| CORS for the preview build | Add `http://localhost:4173` to the development origins in `.env.example` only. |
| Downloads | Files served with `Content-Disposition: attachment`, and the frontend never renders downloaded CSV as HTML. |

## 10. Backend changes needed in Phase 4

All small, read-only or configuration, each with tests and explanation documents, and none touching the model, threshold or saved results:

1. `GET /auth/me` adds the caller's permission list, so the interface mirrors the server's role table instead of copying it.
2. `GET /api/v1/users/assignable` (section 7).
3. `scripts/export_model_report.py`, `artifacts/metadata/model_v1_report.json` and `GET /api/v1/models/report` (section 8).
4. API CSP headers and the trusted-proxy setting (section 9).

**Decision needed:** approve these as part of Phase 4, or limit Phase 4 to the frontend and accept that assignment, the full performance page and the security items wait.

## 11. Testing

| Level | Tools | Covers |
|---|---|---|
| Unit and component | Vitest, React Testing Library, jsdom, user-event | Each component's states. Formatting rules, including no `%` on scores. Guards and permissions. Form validation. Wording and hardcoded-number scans. |
| API contract in the browser | Mock Service Worker, with fixtures typed from `api.generated.ts` | Pages against realistic responses, including 401, 403, 404, 413, 422, 429 and 500, without a server |
| Integration (PRD 14.4) | Playwright against the Docker stack and `vite preview` | Login per role. Predict, then see it stored in the explorer. Batch upload with a bad row, then the error report. Investigation update persists after reload. Dashboard reflects records. Model Performance values equal the saved files. Disclosure visible on every page that shows a score. |
| End to end, browser | Playwright, Chromium | Navigation of all ten pages. Mobile (390 px) and desktop layouts without horizontal scrolling. No CSP violations. Accessibility check on each page with axe. |
| Existing backend suite | pytest | Unchanged, plus tests for the section 10 additions |

- **Test data** is a small, hand-made synthetic sample CSV, labelled as such (PRD 7.6), plus users created by script. Nothing comes from the test partition.
- **Commands:** `npm test`, `npm run test:e2e` and `npm run gen:api:check`.
- **Responsive testing** happens in Playwright, because jsdom has no layout engine.

**Decision needed: end-to-end scope.**

| Option | What Phase 4 includes |
|---|---|
| **A. Recommended** | The Playwright harness and the journeys above in Phase 4. Phase 5 adds the remaining journeys and runs everything in CI. |
| B. | Component tests only in Phase 4, with all Playwright work in Phase 5. Faster, but Phase 4 would then be accepted without proof that pages work against the real backend. |

New development dependencies: `vitest`, `@testing-library/react`, `@testing-library/user-event`, `@testing-library/jest-dom`, `jsdom`, `msw`, `@playwright/test`, `@axe-core/playwright` and `openapi-typescript`. Playwright downloads a Chromium build of about 150 MB.

## 12. Documentation

- A sibling `.explanation.md` for every `.ts`, `.tsx` and `.css` file, written when the file is.
- `package.json`, `tsconfig.json`, `vite.config.ts` and the Playwright and Vitest configs added to the checker's configuration list, each with an explanation.
- `PROJECT_CONNECTIONS.md` sections 13 and 14 rewritten, with frontend flows for login, prediction, batch and investigation.
- `ARCHITECTURE.md`, `TESTING_GUIDE.md` (frontend commands and coverage by PRD 14.3), `ENVIRONMENT_SETUP.md`, `SECURITY.md` (CSP and proxy), `API_DOCUMENTATION.md` (new endpoints) and `CHANGELOG.md`.
- An ADR 0004 for the Phase 4 decisions.

## 13. Milestones

Each is tested before it is committed:

1. Backend additions from section 10, with tests.
2. Frontend foundation: dependencies, API client, generated types, authentication, layout, routing, guards, shared states, `ScoreDisclosure`, test setup.
3. Dashboard, Transaction Analysis, Explainable AI.
4. CSV Batch Analysis, Transaction Explorer.
5. Investigation Centre.
6. Model Performance, Reports, Settings, System Information.
7. Playwright integration and browser tests, CSP and accessibility checks, responsive review, documentation, then the gate report.

## 14. Risks

| Risk | Mitigation |
|---|---|
| Recharts output conflicts with the CSP | Checked in the end-to-end tests. If it does conflict, adjust the policy for style properties only, never scripts, and document it. |
| Generated types drift from the API | The regeneration check fails the test run |
| The model's weak normal-step recall is overlooked by users | Shown on the dashboard and beside every score, not only on the performance page |
| Explanation documents for many small files | Fewer, larger CSS files, and components grouped by page where that keeps them readable |
| Port 8000 belongs to another local project | The frontend's `VITE_API_BASE_URL` points to 8010 locally |
