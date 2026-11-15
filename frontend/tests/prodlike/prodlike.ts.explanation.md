# prodlike.ts

Source: [frontend/tests/prodlike/prodlike.ts](prodlike.ts)

## A. File Purpose
Shared values for the production-like tests.

## B. Why This File Exists
The site, direct API address, database, accounts file and proxy address are used by setup and specs.

## C. Dependencies
- **Libraries:** Node `fs`, `path`.
- **Internal modules:** `../e2e/support.ts`.
- **External services / database:** none.
- **Depended on by:** `global-setup.ts`, `production.spec.ts`.

## D. Every Function Explained

### `prodlikeAccount`
A seeded account from the production-like accounts file; the password is never logged.

## E. Classes Explained
None.

## F. Execution Flow
Imported.

## G. Input and Output
Constants and one reader.

## H. Important Technical Concepts
- **`SITE`, `PLAIN_HTTP`, `DIRECT_API`, `PRODLIKE_DB`, `PRODLIKE_ACCOUNTS`, `CADDY_ADDRESS`** must match the Caddyfile and `docker-compose.yml`.

## I. Example
```ts
const { email } = prodlikeAccount("analyst");
```

## J. Maintenance Notes
Change addresses in all three places together.

## K. Related Files
- [Caddyfile](../../../docker/caddy/Caddyfile.explanation.md): the addresses.
