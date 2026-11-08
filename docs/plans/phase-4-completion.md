# Phase 4 completion: React frontend

Status: complete on branch `phase-4-frontend`, awaiting review. Not merged into `main`, not pushed. Phase 5 has not started.

Plan: [phase-4-plan.md](phase-4-plan.md). Decisions: [ADR 0004](../decisions/0004-phase-4-decisions.md).

## Milestones

| Milestone | Scope | Commit |
|---|---|---|
| M1 | Cookie sessions, CSRF, assignees, model report, security headers and proxy configuration | `9d495a5` |
| M2 | Frontend foundation: typed API client, authentication, layout, shared states | `91846d9` |
| M3 | Dashboard, Transaction Analysis, Explainable AI | `d768db3` |
| M4 | CSV Batch Analysis, Transaction Explorer | `444caf8` |
| M5 | Investigation Centre | `9ff24d3` |
| M6 | Model Performance, Reports, Settings; code-splitting | `cbfd015` |
| M7 | Real-backend browser tests, accessibility and layout fixes, documentation | The commit that adds this file |

## Authorisation decisions and evidence

| Decision | Evidence |
|---|---|
| 1. HttpOnly cookies, CSRF, strict CORS, SameSite, expiry, logout, no browser storage | `auth.spec.ts` in a real browser; `test_sessions.py`; `source-rules.test.ts` scans for browser storage |
| 2. Four backend additions | M1; `test_phase4_backend.py`, `test_model_report.py` |
| 3. Proxy trust off by default | `test_phase4_backend.py`; the browser-test stack sets no trusted proxies |
| 4. Real-backend browser tests with desktop, mobile and accessibility coverage | 103 Playwright tests at three sizes, axe WCAG 2.2 A/AA, 0 violations |
| 5. Model report only from saved Phase 2 outputs | `test_model_report.py`; `model-performance.spec.ts` compares the page with the saved files and their hashes, and sees only GET requests |
| 6. Phase 1–3 behaviour and frozen artefacts preserved | Backend suite 677 passed; model hash and saved results unchanged |
| 7. Explanation documents and PROJECT_CONNECTIONS.md kept current | `check_explanations.py`: 0 problems |
| 8. Seven milestones, each tested and committed | Table above |
| 9. No push without permission | Nothing pushed |
| 10. Stop at the gate | This document; Phase 5 not started |

## Results at the gate

| Suite | Passed | Failed | Skipped | Deselected |
|---|---|---|---|---|
| Backend (pytest) | 677 | 0 | 0 | 1 (rereads the test partition) |
| Frontend unit and component (Vitest) | 98 | 0 | 0 | 0 |
| Browser (Playwright) | 103 | 0 | 0 | 0 |

Browser tests by project: setup 5, desktop 64, tablet 17, mobile 17. Accessibility findings and fixes are in [TESTING_GUIDE.md](../../TESTING_GUIDE.md#accessibility-results).

## Known limitations

See the Phase 4 entry in [CHANGELOG.md](../../CHANGELOG.md) and [SECURITY.md](../../SECURITY.md#known-limitations).
