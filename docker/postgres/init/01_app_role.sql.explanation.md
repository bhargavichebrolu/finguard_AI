# 01_app_role.sql

Source: [docker/postgres/init/01_app_role.sql](01_app_role.sql)

## A. File Purpose
Runs once when a new data volume is initialised. It creates the login role the API uses and a separate test database, and hands the main database to that role.

## B. Why This File Exists
PRD section 10 requires database access controls. An API connecting as a superuser could read or change anything on the server if it were compromised. This role has no superuser, role-creation or database-creation rights.

## C. Dependencies
- **Libraries / tools:** `psql` 15 or later, for `\getenv`.
- **Internal files:** mounted into the container by `docker-compose.yml`.
- **External services / database:** run by the official image's first-start process, as `POSTGRES_USER`.
- **Depended on by:** `DATABASE_URL` and `TEST_DATABASE_URL`, which connect as this role.

## D. Every Function Explained
No functions: this is a SQL script.

### Statements
- `\set ON_ERROR_STOP on` makes the first error fatal, so a half-configured database is never left looking finished.
- `\getenv` reads values from the container's environment into `psql` variables. The password is therefore not written in this file.
- `CREATE ROLE ... NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION` states the restrictions explicitly. `:'app_password'` quotes the value as a literal and `:"app_user"` as an identifier, which is `psql`'s own safe quoting.
- `ALTER DATABASE ... OWNER` lets migrations create tables. In PostgreSQL 15 and later the `public` schema belongs to the database owner.
- `CREATE DATABASE :"test_db"` gives tests a database they can empty without touching development data.

## E. Classes Explained
None.

## F. Execution Flow
The image runs files in `/docker-entrypoint-initdb.d` in name order, only when the data directory is empty. It is skipped on later starts.

## G. Input and Output
Input: `APP_DB_USER`, `APP_DB_PASSWORD`, `TEST_DB_NAME`, `POSTGRES_DB`. Output: one role, one new database, and one changed owner.

## H. Important Technical Concepts
- **Runs only on first initialisation.** Changing this file has no effect on an existing volume.
- **SCRAM storage.** `password_encryption` defaults to `scram-sha-256`, so the server stores a salted verifier rather than the password. Diagnostics confirmed this for both roles.

## I. Example
```sql
-- Confirm the role's limits, as the superuser:
select rolname, rolsuper, rolcreatedb, rolcreaterole from pg_roles where rolname = 'finguard_app';
```

## J. Maintenance Notes
This file must keep LF line endings, enforced by `.gitattributes`, since it runs inside a Linux container. To change a password later, use `ALTER ROLE` and update `.env`.

## K. Related Files
- [docker-compose.yml](../../../docker-compose.yml.explanation.md): mounts this file and supplies its values.
- [.env.example](../../../.env.example.explanation.md): the variables.
