-- PROPOSED B0 only; requires fresh owner authorization. Not executed.
-- One catalog-only snapshot for choosing backup coverage, not a data backup.
-- No table rows, exact row counts, password hashes, Vault secrets or function bodies.
BEGIN TRANSACTION READ ONLY;
SET LOCAL statement_timeout='1500ms';
SET LOCAL lock_timeout='250ms';
SET LOCAL idle_in_transaction_session_timeout='1500ms';
SELECT datname,pg_get_userbyid(datdba) AS owner,datacl::text
 FROM pg_database WHERE datname=current_database();
SELECT nspname,pg_get_userbyid(nspowner) AS owner,nspacl::text
 FROM pg_namespace
 WHERE nspname NOT LIKE 'pg_%' AND nspname<>'information_schema'
 ORDER BY nspname LIMIT 513;
SELECT n.nspname,c.relname,c.relkind,pg_get_userbyid(c.relowner) AS owner,
       c.relacl::text,c.relrowsecurity,c.relforcerowsecurity,
       c.reltuples AS estimated_rows_not_a_data_count,
       e.extname AS extension_owner
 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
 LEFT JOIN pg_depend d ON d.classid='pg_class'::regclass AND d.objid=c.oid AND d.deptype='e'
 LEFT JOIN pg_extension e ON e.oid=d.refobjid
 WHERE n.nspname IN ('public','whereto','provider_state','provider_rules','private_runtime')
 ORDER BY n.nspname,c.relname LIMIT 4097;
SELECT n.nspname,p.proname,pg_get_function_identity_arguments(p.oid) AS arguments,
       pg_get_userbyid(p.proowner) AS owner,p.proacl::text,e.extname AS extension_owner
 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
 LEFT JOIN pg_depend d ON d.classid='pg_proc'::regclass AND d.objid=p.oid AND d.deptype='e'
 LEFT JOIN pg_extension e ON e.oid=d.refobjid
 WHERE n.nspname IN ('public','whereto','provider_state','provider_rules','private_runtime')
 ORDER BY n.nspname,p.proname,arguments LIMIT 4097;
SELECT pg_get_userbyid(a.defaclrole) AS owner,n.nspname,a.defaclobjtype,a.defaclacl::text
 FROM pg_default_acl a LEFT JOIN pg_namespace n ON n.oid=a.defaclnamespace
 WHERE n.nspname IS NULL OR n.nspname IN ('public','whereto','provider_state','provider_rules','private_runtime')
 ORDER BY owner,n.nspname,a.defaclobjtype LIMIT 513;
SELECT rolname,rolcanlogin,rolsuper,rolcreatedb,rolcreaterole,rolreplication,
       rolbypassrls,rolconnlimit
 FROM pg_roles WHERE rolname IN ('postgres','whereto_plan_runtime')
 OR rolname LIKE 'whereto\_%' ESCAPE '\' OR rolname LIKE 'real\_%' ESCAPE '\'
 ORDER BY rolname LIMIT 513;
SELECT child.rolname AS member,parent.rolname AS parent,m.admin_option
 FROM pg_auth_members m JOIN pg_roles child ON child.oid=m.member
 JOIN pg_roles parent ON parent.oid=m.roleid
 WHERE child.rolname IN ('postgres','whereto_plan_runtime')
 OR child.rolname LIKE 'whereto\_%' ESCAPE '\' OR child.rolname LIKE 'real\_%' ESCAPE '\'
 ORDER BY child.rolname,parent.rolname LIMIT 513;
SELECT e.extname,e.extversion,n.nspname AS schema
 FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace ORDER BY e.extname LIMIT 513;
ROLLBACK;
-- Limits are overflow sentinels, not successful truncation: refuse at 513/4097.
-- RLS policy detail/sequence comparison is in backup-restore-verify-readonly-v1.sql.
-- Captured baselines stay owner-only; select exact backup coverage before export.
