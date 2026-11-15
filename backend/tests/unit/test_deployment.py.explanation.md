# test_deployment.py

Source: [backend/tests/unit/test_deployment.py](test_deployment.py)

## A. File Purpose
Checks the production deployment files as text: the Compose file, the production Caddyfile, the web and API Dockerfiles, the web build's ignore file, the database script, the CI image job and the production settings generator.

## B. Why This File Exists
Phase 6 added a production configuration whose safety depends on details that are easy to break in an edit: only Caddy publishes ports, the API trusts only Caddy's fixed address, secrets have no defaults, the site policy matches everywhere, the model is mounted read-only, and the web build context excludes the dataset, model and secrets. These tests run in CI without Docker.

## C. Dependencies
- **Libraries:** pytest, `re`.
- **Internal modules:** `scripts/generate_production_env.py`, through the `load_script` fixture.
- **External services / database:** none.
- **Depended on by:** none; run by pytest and CI.

## D. Every Function Explained

### `service`
Returns one service's block from `docker-compose.prod.yml`, so a test can look at that service alone.

### `csp`
Returns the Content-Security-Policy value from a Caddyfile.

### `generator`
Fixture: the production settings generator module.

### `grid`
Fixture: the reference-grid script module.

### `api_handler`
Returns the whole `handle @api` block of the production Caddyfile, up to the static-file handler, so checks cover every line that applies to API requests.

**Common to every test below:** failures surface as `AssertionError`. pytest runs them.

| Function | Proves |
|---|---|
| `test_the_site_policy_is_the_same_everywhere` | Production and production-like Caddyfiles send the same CSP, with HSTS and no `Server` header. |
| `test_api_responses_are_never_compressed` | Compression is only for static files (BREACH). |
| `test_the_api_trusts_only_caddys_fixed_address` | `TRUSTED_PROXY_IPS` is exactly Caddy's fixed address in the fixed subnet (S14). |
| `test_only_caddy_publishes_ports` | The database, migrations, API and retention publish no port; the database is not on Caddy's network. |
| `test_production_settings_and_no_committed_secrets` | `APP_ENV=production`; every secret is required with no default; documentation stays off; no test database. |
| `test_frozen_model_is_mounted_read_only` | The model folder is mounted `:ro`. |
| `test_base_images_are_pinned_by_digest` | Every `FROM` line and the database image use `@sha256:`. |
| `test_the_web_build_context_excludes_data_models_and_secrets` | The ignore file starts with `*` and allows only `frontend/` and the production Caddyfile. |
| `test_the_api_image_ships_no_installer_and_no_gpu_library` | uv is installed only in the build stage, and the lock removes NVIDIA NCCL. |
| `test_the_database_script_creates_a_test_database_only_when_named` | The init script creates the test database only when `TEST_DB_NAME` is set. |
| `test_generated_file_supplies_every_required_variable` | The generator provides every `${VAR:?}` the Compose file requires, with new secrets each time. |
| `test_the_origin_names_a_non_default_port` | The public origin includes a port only when it is not 443. |
| `test_bad_inputs_are_refused_before_anything_is_written` | `localhost`, a URL instead of a host name, and a non-email `--tls` are refused. |
| `test_an_existing_file_is_never_overwritten` | An existing settings file is left untouched. |
| `test_the_production_env_file_is_ignored_by_git` | `.env.*` stays in `.gitignore`. |
| `test_ci_builds_both_images_and_checks_the_production_configuration` | The CI `images` job builds both images and validates the Compose file. |
| `test_the_reference_grid_covers_every_valid_input_kind` | The inference-parity grid has 550 rows, every type, and merchant only with PAYMENT. |
| `test_the_fingerprint_changes_with_any_output` | The fingerprint is stable for equal outputs and changes when one score or one explanation value changes in its last digits. |
| `test_the_proxy_caps_request_bodies_above_the_upload_limit` | The API handler limits request bodies to 11 MB before proxying, so an upload without `Content-Length` is stopped while it streams. |

## E. Classes Explained
None.

## F. Execution Flow
The files are read once at import; each test inspects them.

## G. Input and Output
Input: committed configuration files. Output: assertions.

## H. Important Technical Concepts
These are static checks. The running stack is checked by the local production rehearsal with `scripts/verify_deployment.py` (DEPLOYMENT.md) and by the HTTPS browser tests.

## I. Example
```powershell
uv run --project backend pytest backend/tests/unit/test_deployment.py -q
```

## J. Maintenance Notes
If Caddy's address or subnet changes, change `TRUSTED_PROXY_IPS` with it; this test fails until both agree.

## K. Related Files
- [docker-compose.prod.yml](../../../docker-compose.prod.yml.explanation.md)
- [Caddyfile.production](../../../docker/caddy/Caddyfile.production.explanation.md)
- [generate_production_env.py](../../../scripts/generate_production_env.py.explanation.md)
