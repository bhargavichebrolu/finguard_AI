# ADR 0006: Phase 6 decisions (deployment and release)

Status: implemented on branch `phase-5-hardening`, 2026-11-15. Phase 5 was accepted on 2026-11-13 with its documented residual risks (the unexplained single Firefox status-change failure, the Firefox teardown hang under CPU starvation, untested Safari and screen readers, and WebKit's SameSite enforcement). Each decision below follows an earlier project decision or a recorded finding; none changes the frozen model, its threshold, its features or its preprocessing.

## D1. One Docker host with Caddy, rather than separate platforms

The PRD's target named Netlify or Vercel for the interface, a container host for the API, and managed PostgreSQL. Phase 6 deploys all of it with one Compose file instead: Caddy, the API, PostgreSQL, migrations and retention.

**Why:**
- ADR 0004 requires the browser to reach the API on its own origin, so SameSite=Strict cookies work. Caddy already does this in the Phase 5 production-like stack, and its HTTPS behaviour is tested.
- The batch queue and rate limits live in PostgreSQL (ADR 0005), so no platform-specific worker or cache is needed.
- No host account or domain was available to this project, so a configuration that runs identically on any Docker host is the one that could be verified.

The images and Caddy rules carry over to a platform. `TRUSTED_PROXY_IPS` must then list that platform's proxies.

## D2. No API documentation in production (security finding S13)

`/docs`, `/redoc` and `/openapi.json` are off when `APP_ENV=production`, and `API_DOCS_ENABLED=true` is refused there. Development and test keep them.

**Why:** the pages need a looser CSP (CDN scripts and inline code), and they list every route to anyone. The contract is already published as `API_DOCUMENTATION.md` and the committed `frontend/openapi.json`. Self-hosting Swagger UI was the alternative, but it would add files to maintain for no user of the deployed site.

## D3. Production requires a trusted proxy, named exactly (security finding S14)

Production refuses to start with an empty `TRUSTED_PROXY_IPS`, and every environment refuses entries that are not IP addresses or networks, or that cover every address.

**Why:**
- Production cookies need HTTPS, which the API never terminates, so a production API always has a proxy in front.
- Without the proxy's address, every client appears to be the proxy, and the sign-in limit becomes per email for everyone.
- Strict parsing also refuses `10.0.0.5/24`, which would otherwise crash uvicorn at start-up.

## D4. Shrink the API image without changing the model's libraries (finding F12)

- NVIDIA NCCL is removed through a `uv` override.
- uv is used only in a build stage.

The image went from 1.92 GB to 979 MB.

**Why not `xgboost-cpu`:** start-up checks the installed `xgboost` distribution's version against the model's metadata. Switching packages would mean changing that check, which protects the frozen model.

**Proof:** 550 synthetic inputs, run through the old and new images, gave byte-for-byte identical scores and SHAP values.

## D5. Deferred join for the explorer, not keyset pagination

The explorer's page query now sorts and skips transaction identifiers alone, then joins the full rows for that page only.

**Results** (180,285 stored transactions, same rows returned):

| Page | Before | After |
|---|---|---|
| Last page | 392 ms | 79 ms |
| Middle page, sorted by score | 545 ms | 76 ms |

**Why not keyset pagination:** it would change the API (a cursor instead of `offset`) and the interface's pager, and drop "page N of M". The interface moves one page at a time, so the remaining cost of `OFFSET` falls only on API clients asking for very deep pages.

## D6. Proxy body limit of 11 MB

Caddy refuses API request bodies over 11 MB while they stream.

**Why:** an upload sent without `Content-Length` was spooled by the framework before the API's 10 MB check (a Phase 5 limitation). The limit leaves room for multipart wrapping around a 10 MB file.

## D7. Operations inside the image

- The administrator command moved to `app/commands/create_admin.py`, so the first account can be created inside the running container. `scripts/create_admin.py` now calls it.
- Retention runs as a service that applies the approved periods once a day, so it needs no host scheduler.

## D8. Browser-test sessions last 120 minutes

Only the browser-test API sets `ACCESS_TOKEN_MINUTES=120`.

**Why:** the Phase 5 investigation showed that runs on a loaded machine outlived the setup project's 30-minute sessions. Expiry itself is tested by revoking sessions, not by waiting. Production keeps 30 minutes.

## Reviewed and kept

| Item | Kept because |
|---|---|
| Fixed-window prediction and upload limits | Up to twice the limit can pass across a minute boundary. Phase 5 M3 measured that the sliding window broke the latency budget, so failed sign-ins keep the strict sliding window and the rest stay fixed. |
| Batch recovery, multi-process queue, connection handling and outages | Unchanged from Phase 5. The production rehearsal repeated the database outage and full restart, and both recovered. |
| Last writer wins on assignment | Every change is audited, and status changes already carry `expected_status`. |

## Not done

- Deployment to a public host, a public certificate, and a public URL: no host or domain was available.
- Pushing, merging into `main`, and running CI on GitHub.
- Manual screen-reader testing, which needs a person.
- Testing in Safari on macOS.
