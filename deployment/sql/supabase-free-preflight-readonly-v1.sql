-- PREPARATION ONLY. One separately authorized direct IPv6/TLS operator session.
-- No application rows, password catalogs, SQL/query text or provider operations.
BEGIN TRANSACTION READ ONLY;
SET LOCAL statement_timeout = '1500ms';
SET LOCAL lock_timeout = '250ms';
SET LOCAL idle_in_transaction_session_timeout = '1500ms';
SELECT current_database() AS database, session_user, current_user,
       current_setting('server_version_num')::integer / 10000 AS server_major,
       current_setting('server_version') AS server_version,
       current_setting('transaction_read_only') AS read_only,
       current_setting('statement_timeout') AS statement_timeout,
       current_setting('lock_timeout') AS lock_timeout,
       pg_backend_pid() AS backend_pid,
       family(inet_client_addr()) AS client_address_family,
       family(inet_server_addr()) AS server_address_family;
SELECT ssl, version, cipher, bits FROM pg_stat_ssl WHERE pid=pg_backend_pid();
-- The client MUST independently enforce sslmode=verify-full, pinned CA/hostname
-- and connect_timeout=2. pg_stat_ssl alone does not prove certificate validation.
SELECT name, setting, unit FROM pg_settings
 WHERE name IN ('max_connections','superuser_reserved_connections',
                'shared_buffers','work_mem','maintenance_work_mem') ORDER BY name;
SELECT count(*) AS total_connections,
       count(*) FILTER (WHERE datname=current_database()) AS database_connections,
       count(*) FILTER (WHERE backend_type='client backend') AS client_backends,
       count(*) FILTER (WHERE state='active') AS visible_active_connections
 FROM pg_stat_activity;
-- Activity details may be hidden from restricted users. Do not infer CPU/RAM
-- entitlement, all reserved slots or sustained headroom from these counts.
SELECT rolname, rolcanlogin, rolsuper, rolcreatedb, rolcreaterole, rolreplication,
       rolbypassrls, rolconnlimit,
       has_database_privilege(rolname,current_database(),'CONNECT') AS can_connect,
       has_database_privilege(rolname,current_database(),'CREATE') AS can_create
 FROM pg_roles
 WHERE rolname=session_user OR rolname='whereto_plan_runtime'
    OR rolname LIKE 'whereto_real_%' OR rolname LIKE 'real\_%' ESCAPE '\'
 ORDER BY rolname LIMIT 128;
SELECT child.rolname AS member, parent.rolname AS parent, m.admin_option
 FROM pg_auth_members m JOIN pg_roles child ON child.oid=m.member
 JOIN pg_roles parent ON parent.oid=m.roleid
 WHERE child.rolname=session_user OR child.rolname='whereto_plan_runtime'
    OR child.rolname LIKE 'whereto_real_%' OR child.rolname LIKE 'real\_%' ESCAPE '\'
 ORDER BY child.rolname,parent.rolname LIMIT 256;
-- Real-profile names above are fixture-derived candidates, NOT enrolled logins.
SELECT nspname,pg_get_userbyid(nspowner) AS owner
 FROM pg_namespace WHERE nspname IN
 ('public','whereto','provider_state','provider_rules','provider_witness','private_runtime')
 ORDER BY nspname;
SELECT extname,extversion FROM pg_extension ORDER BY extname;
-- Core SHA256/UUID and plpgsql are required; do not install pgcrypto needlessly.
SELECT to_regprocedure('pg_catalog.sha256(bytea)') IS NOT NULL AS core_sha256,
       to_regprocedure('pg_catalog.gen_random_uuid()') IS NOT NULL AS core_uuid,
       EXISTS(SELECT 1 FROM pg_language WHERE lanname='plpgsql') AS plpgsql;
SELECT pg_database_size(current_database()) AS database_bytes,
       xact_commit,xact_rollback,blks_read,blks_hit,temp_bytes,deadlocks
 FROM pg_stat_database WHERE datname=current_database();
-- Absence of provider_* schemas is expected before approved installation.
-- This catalog probe never invokes financial/enrollment/restore functions.
-- Version acceptance remains17-only; incompatible targets must not be enrolled.
SELECT '{"probe":1}' IS JSON OBJECT WITH UNIQUE KEYS AS unique_json_contract;
ROLLBACK;
