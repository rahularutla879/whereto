-- Review-only catalog probe. No credential loading or target connection here.
-- Operator uses an existing protected direct/session-affine PostgreSQL connection.
-- Output is metadata only; do not select query text, parameters or table contents.
BEGIN TRANSACTION READ ONLY;
SET LOCAL statement_timeout = '1500ms';
SET LOCAL lock_timeout = '250ms';
SET LOCAL idle_in_transaction_session_timeout = '1500ms';
SELECT current_database() AS database, session_user, current_user,
       current_setting('server_version') AS server_version,
       current_setting('max_connections')::integer AS max_connections,
       current_setting('superuser_reserved_connections')::integer AS reserved_superuser_connections,
       pg_backend_pid() AS backend_pid;
SELECT ssl, version, cipher, bits FROM pg_stat_ssl WHERE pid=pg_backend_pid();
SELECT count(*) AS total_connections,
       count(*) FILTER (WHERE datname=current_database()) AS database_connections,
       count(*) FILTER (WHERE state='active') AS active_connections
FROM pg_stat_activity;
SELECT rolname, rolcanlogin, rolsuper, rolcreatedb, rolcreaterole,
       rolreplication, rolbypassrls, rolconnlimit
FROM pg_roles WHERE rolname=session_user;
SELECT nspname, pg_get_userbyid(nspowner) AS owner
FROM pg_namespace WHERE nspname IN ('whereto','provider_state','provider_rules','provider_witness','private_runtime');
SELECT has_database_privilege(session_user,current_database(),'CREATE') AS database_create,
       pg_database_size(current_database()) AS database_bytes;
ROLLBACK;
