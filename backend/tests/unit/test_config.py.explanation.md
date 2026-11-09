# test_config.py

Source: [backend/tests/unit/test_config.py](test_config.py)

## A. File Purpose
Tests that `Settings` refuses unsafe configuration, hides secrets, and that the frozen constants match Phase 2.

## B. Why This File Exists
Start-up validation is a security control only if it actually rejects bad values. These tests prove each rejection.

## C. Dependencies
- **Libraries:** `pytest`, `pydantic`.
- **Internal modules:** `app.core.config`, `app.core.frozen_model`.
- **External services / database:** none. `_env_file=None` stops the real `.env` being read.
- **Depended on by:** none; run by pytest.

## D. Every Function Explained

### `build`
- **Purpose:** create settings from good values with some overridden.
- **Parameters / types:** keyword overrides. **Returns / type:** `Settings`.
- **Internal processing:** merges with `GOOD`.
- **Error handling:** validation errors propagate to the test.
- **Calls:** `Settings`. **Used by:** every test here.

**Common to every test below:** failures surface as `AssertionError` or a `pytest.raises` failure. pytest runs them.

| Function | Proves |
|---|---|
| `test_valid_settings_are_accepted` | Good values work. |
| `test_secret_key_cannot_be_short` | A short key stops start-up. |
| `test_secret_key_cannot_be_the_template_value` | The `.env.example` placeholder is refused. |
| `test_database_url_cannot_be_the_template_value` | The template's password is refused. |
| `test_wildcard_cors_is_refused_everywhere` | `*` is refused in every environment. |
| `test_production_refuses_localhost_origins` | Production cannot allow `localhost`. |
| `test_production_refuses_per_process_rate_limits` | Production must store rate limits in the database (Phase 5 M3). |
| `test_production_accepts_a_real_origin` | Real origins are parsed into a list. |
| `test_secrets_do_not_appear_when_settings_are_printed` | `repr` hides the password and key. |
| `test_validation_error_does_not_contain_the_secret` | The error detail, without its input field, omits a rejected key. |
| `test_frozen_values_match_phase_2` | The pinned threshold, hash and calibration flag are as frozen. |

## E. Classes Explained
None.

## F. Execution Flow
pytest calls each test, and each builds its own settings object.

## G. Input and Output
Input: literal values. Output: pass or fail.

## H. Important Technical Concepts
- **`_env_file=None`:** tests must not depend on a developer's `.env`.

## I. Example
```powershell
uv run --project backend pytest backend/tests/unit/test_config.py
```

## J. Maintenance Notes
New validators need a test here. `test_frozen_values_match_phase_2` should change only with a deliberate new model release.

## K. Related Files
- [config.py](../../app/core/config.py.explanation.md): the code under test.
- [frozen_model.py](../../app/core/frozen_model.py.explanation.md): the constants.
