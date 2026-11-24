-- PREPARED read-only metadata comparison for a separately authorized DISPOSABLE
-- restore. Run before/after using a quiescent source and the same schema scope.
-- NOT a complete backup verifier: require independent row/sequence/role checks.
BEGIN TRANSACTION READ ONLY;
SET LOCAL statement_timeout='1500ms';
SET LOCAL lock_timeout='250ms';
SET LOCAL idle_in_transaction_session_timeout='1500ms';
WITH objects AS (
 SELECT n.nspname,c.relname,c.relkind,pg_get_userbyid(c.relowner) AS owner,
        c.relacl::text,c.relrowsecurity,c.relforcerowsecurity
 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
 WHERE n.nspname IN ('public','whereto','provider_state','provider_rules','provider_witness','private_runtime')
), policies AS (
 SELECT n.nspname,c.relname,p.polname,p.polcmd,p.polpermissive,
        ARRAY(SELECT CASE WHEN role_oid=0 THEN 'PUBLIC' ELSE pg_get_userbyid(role_oid) END FROM unnest(p.polroles) AS role_oid ORDER BY 1) AS roles,
        pg_get_expr(p.polqual,p.polrelid) AS qualifier,
        pg_get_expr(p.polwithcheck,p.polrelid) AS with_check
 FROM pg_policy p JOIN pg_class c ON c.oid=p.polrelid JOIN pg_namespace n ON n.oid=c.relnamespace
 WHERE n.nspname IN ('public','whereto','provider_state','provider_rules','provider_witness','private_runtime')
)
SELECT 'relations' AS category,encode(sha256(convert_to(coalesce(
 (SELECT jsonb_agg(to_jsonb(o) ORDER BY nspname,relname)::text FROM objects o),'[]'),'UTF8')),'hex') AS sha256
UNION ALL
SELECT 'row_security',encode(sha256(convert_to(coalesce(
 (SELECT jsonb_agg(to_jsonb(p) ORDER BY nspname,relname,polname)::text FROM policies p),'[]'),'UTF8')),'hex');
-- Report sequence metadata only. A verifier must additionally compare actual
-- last_value/is_called under the approved quiescent window, not call nextval().
SELECT schemaname,sequencename,sequenceowner,data_type,start_value,min_value,
       max_value,increment_by,cycle,cache_size,last_value
 FROM pg_sequences WHERE schemaname IN
 ('public','whereto','provider_state','provider_rules','provider_witness','private_runtime')
 ORDER BY schemaname,sequencename;
ROLLBACK;
