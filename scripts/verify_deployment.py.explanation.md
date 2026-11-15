# verify_deployment.py

Source: [scripts/verify_deployment.py](verify_deployment.py)

## A. File Purpose
Checks a running deployment through its public HTTPS origin, as a browser would: health, security headers, no published API schema, sign-in cookies, the CSRF and origin checks, the frozen model's identity, and sign-out. With `--write` it also scores one transaction and runs a three-row batch.

## B. Why This File Exists
Phase 6 requires deployment verification, not only unit tests of configuration. This script turns the checks into a repeatable command that prints PASS or FAIL per check, for the local rehearsal and for a real host.

## C. Dependencies
- **Libraries:** standard library only (`urllib`, `http.cookiejar`, `ssl`, `json`).
- **Internal modules:** none, so it runs from any computer with Python 3.11.
- **External services / database:** the deployed site.
- **Depended on by:** `DEPLOYMENT.md`, `TESTING_GUIDE.md`.

## D. Every Function Explained

### `Answer`
A response: status, lower-cased headers, every `Set-Cookie` line, and the body; `json` parses the body.

### `Client`
Holds the origin, the TLS context and a cookie jar. `request` sends one request (following redirects unless `follow` is false); `cookie` reads a stored cookie's value.

### `_NoRedirect`
A redirect handler whose `redirect_request` returns nothing, so a redirect is reported instead of followed.

### `_answer`
Builds an `Answer` from a response or an HTTP error.

### `Report`
Counts failures; `__init__` starts the count at zero, and `check` prints one PASS or FAIL line.

### `check_site`
Health, the interface, HSTS, CSP, `nosniff`, no `Server` header, no API schema, and the API's own policy on API answers.

### `sign_in`
Signs in through `/api/v1/auth/session` and checks the `__Secure-` session cookie (HttpOnly, Secure, SameSite=Strict, Path=/api), the `__Host-` CSRF cookie (readable, Secure, SameSite=Strict, Path=/), and that no token is in the body.

### `check_signed_in`
Reads the account and the system status: production environment, database available, model hash prefix `69813c17` and threshold `0.02841914258897305`.

### `_write_headers`
The headers for a change: JSON, `Origin`, and the CSRF token from the cookie.

### `check_csrf`
A change without the token, and one from another origin, must both be refused with 403.

### `check_writes`
Scores one transaction (expects 201, an uncalibrated score, the frozen threshold, one of the two decisions) and uploads a three-row CSV, polling until the queue completes it. Identifiers start with `VERIFY-`.

### `sign_out`
Signs out and confirms the session no longer works.

### `main`
Parses arguments, reads the password from `FINGUARD_ADMIN_PASSWORD` or a prompt, runs the checks, and returns the number of failures as the exit code.

## E. Classes Explained
`Answer`, `Client`, `_NoRedirect` and `Report`, described above.

## F. Execution Flow
Site checks → sign in → signed-in checks → CSRF checks → optional writes → sign out → summary.

## G. Input and Output
Input: `--origin`, `--email`, optional `--ca-file` and `--write`. Output: PASS/FAIL lines; exit code 0 when everything passed.

## H. Important Technical Concepts
- **Certificates are verified.** For a private authority (the `internal` rehearsal), pass its root with `--ca-file`; there is no option to skip verification.
- **Writes are opt-in**, because they store data in the deployment.

## I. Example
```powershell
$env:FINGUARD_ADMIN_PASSWORD = "..."   # or omit it to be prompted
python scripts/verify_deployment.py --origin https://finguard.example.com --email admin@example.com
```

## J. Maintenance Notes
If cookie names or routes change, update the constants and paths here with them.

## K. Related Files
- [docker-compose.prod.yml](../docker-compose.prod.yml.explanation.md)
- [production.spec.ts](../frontend/tests/prodlike/production.spec.ts.explanation.md): the browser-level HTTPS tests.
