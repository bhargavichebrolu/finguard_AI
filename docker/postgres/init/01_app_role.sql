-- Runs once, when the data volume is first initialised, as the POSTGRES_USER superuser.
-- Creates the role the API uses, which is not a superuser, and a separate test database.
-- Values come from the container's environment. No credential is stored in this file.

\set ON_ERROR_STOP on
\getenv app_user APP_DB_USER
\getenv app_password APP_DB_PASSWORD
\getenv test_db TEST_DB_NAME
\getenv main_db POSTGRES_DB

CREATE ROLE :"app_user" LOGIN PASSWORD :'app_password'
    NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;

ALTER DATABASE :"main_db" OWNER TO :"app_user";
CREATE DATABASE :"test_db" OWNER :"app_user";
