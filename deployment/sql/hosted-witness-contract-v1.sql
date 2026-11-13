-- Reviewed inert installer: isolated operational database only; never run by workers.
-- No financial grant, clock override, reset, migration of saved data or credential.
SET ROLE whereto_synthetic_owner;
CREATE SCHEMA private_runtime;
REVOKE ALL ON SCHEMA private_runtime FROM PUBLIC;
CREATE TABLE private_runtime.enrollment(principal name PRIMARY KEY,purpose text NOT NULL CHECK(purpose IN ('runtime','issuer','counter','delivery','nonce','witness-factory','witness-counter','witness-delivery','recovery')),contract text NOT NULL CHECK(contract ~ '^[0-9a-f]{64}$'));
REVOKE ALL ON private_runtime.enrollment FROM PUBLIC;
CREATE FUNCTION private_runtime.measure() RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE stamp jsonb;cfg jsonb;
BEGIN
IF EXISTS(SELECT 1 FROM grant_rules.test_clock WHERE value IS NOT NULL) THEN RAISE EXCEPTION 'test_clock_forbidden'; END IF;
 SELECT jsonb_build_object(
 'functions',(SELECT jsonb_agg(jsonb_build_array(n.nspname,p.proname,pg_get_function_identity_arguments(p.oid),pg_get_functiondef(p.oid),p.proowner::regrole::text,p.proacl::text) ORDER BY n.nspname,p.proname,pg_get_function_identity_arguments(p.oid)) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname=ANY(ARRAY['witness','grant_rules','private_runtime']::text[]) AND p.prokind IN ('f','p')),
 'relations',(SELECT jsonb_agg(jsonb_build_array(n.nspname,c.relname,c.relkind,c.relowner::regrole::text,c.relacl::text,c.relrowsecurity,c.relforcerowsecurity) ORDER BY n.nspname,c.relname) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=ANY(ARRAY['witness','grant_rules','private_runtime']::text[])),
 'columns',(SELECT jsonb_agg(jsonb_build_array(n.nspname,c.relname,a.attnum,a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,pg_get_expr(d.adbin,d.adrelid)) ORDER BY n.nspname,c.relname,a.attnum) FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace LEFT JOIN pg_attrdef d ON d.adrelid=c.oid AND d.adnum=a.attnum WHERE n.nspname=ANY(ARRAY['witness','grant_rules','private_runtime']::text[]) AND a.attnum>0 AND NOT a.attisdropped),
 'constraints',(SELECT jsonb_agg(jsonb_build_array(n.nspname,c.relname,k.conname,pg_get_constraintdef(k.oid)) ORDER BY n.nspname,c.relname,k.conname) FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=ANY(ARRAY['witness','grant_rules','private_runtime']::text[])),
 'triggers',(SELECT jsonb_agg(pg_get_triggerdef(t.oid) ORDER BY n.nspname,c.relname,t.tgname) FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=ANY(ARRAY['witness','grant_rules','private_runtime']::text[]) AND NOT t.tgisinternal)) INTO stamp;
 SELECT jsonb_build_object('grant',(SELECT to_jsonb(p) FROM grant_rules.configuration p WHERE id=1),'control',(SELECT jsonb_build_object('epoch',epoch) FROM witness.epochs ORDER BY sequence DESC LIMIT 1)) INTO cfg;
 IF cfg IS NULL OR EXISTS(SELECT 1 FROM jsonb_each(cfg) e WHERE e.value='null'::jsonb) THEN RAISE EXCEPTION 'hosted_policy_missing'; END IF;
 RETURN encode(sha256(convert_to(jsonb_build_object('version','52-hosted-storage-contract-v1','ddl',stamp,'policy',cfg)::text,'UTF8')),'hex');
END $$;
REVOKE ALL ON FUNCTION private_runtime.measure() FROM PUBLIC;
CREATE FUNCTION private_runtime.connection_identity() RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE expected text;scope text;
BEGIN
 SELECT contract,purpose INTO STRICT expected,scope FROM private_runtime.enrollment WHERE principal=session_user;
 IF private_runtime.measure() IS DISTINCT FROM expected THEN RAISE EXCEPTION 'hosted_contract_changed'; END IF;
 RETURN jsonb_build_object('contract',expected,'purpose',scope);
END $$;
REVOKE ALL ON FUNCTION private_runtime.connection_identity() FROM PUBLIC;
CREATE FUNCTION private_runtime.assert_session(expected integer) RETURNS boolean LANGUAGE plpgsql VOLATILE SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 IF expected IS NULL OR pg_backend_pid()<>expected OR NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname=session_user AND rolcanlogin AND coalesce(rolvaliduntil>clock_timestamp(),true)) THEN RAISE EXCEPTION 'connection_affinity_lost'; END IF;
 RETURN true;
END $$;
REVOKE ALL ON FUNCTION private_runtime.assert_session(integer) FROM PUBLIC;
RESET ROLE;
-- The separately authenticated installer must grant schema USAGE / function EXECUTE
-- only to reviewed login roles, then store measure() as each role's enrollment.
-- Publish that exact expected hash to independently managed service configuration.
-- Runtime cannot enroll itself or execute measure(). No grants appear in this file.
