-- v2: canonical semantic ACLs; preserve every privilege/grantor/grantee/grantability.
-- PROPOSED B1 only. Explicit operator/data-read approval required; NOT executed.
-- Output is private baseline metadata/digests, never raw application rows.
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL statement_timeout='1500ms';
SET LOCAL lock_timeout='250ms';
SET LOCAL idle_in_transaction_session_timeout='1500ms';
SET LOCAL timezone='UTC';
SET LOCAL datestyle='ISO, YMD';
-- This setting refuses RLS-filtered reads; it does not bypass or ALTER RLS.
SET LOCAL row_security=off;
SELECT jsonb_build_object('fact','database','encoding',pg_encoding_to_char(encoding),
 'collate',datcollate,'ctype',datctype,'locale_provider',datlocprovider,
 'source_version',current_setting('server_version'))
 FROM pg_database WHERE datname=current_database();
-- No rolpassword, rolconfig, Vault, function bodies or platform credential export.
SELECT jsonb_build_object('fact','application_roles','roles',jsonb_agg(to_jsonb(r) ORDER BY rolname))
 FROM (SELECT rolname,rolsuper,rolinherit,rolcreaterole,rolcreatedb,rolcanlogin,
 rolreplication,rolbypassrls,rolconnlimit,rolvaliduntil
 FROM pg_roles WHERE rolname IN ('postgres','whereto_plan_runtime')) r;
SELECT jsonb_build_object('fact','role_membership_metadata','memberships',jsonb_agg(to_jsonb(m) ORDER BY member,parent,grantor))
 FROM (SELECT child.rolname AS member,parent.rolname AS parent,grantor.rolname AS grantor,
 a.admin_option,a.inherit_option,a.set_option
 FROM pg_auth_members a JOIN pg_roles child ON child.oid=a.member
 JOIN pg_roles parent ON parent.oid=a.roleid JOIN pg_roles grantor ON grantor.oid=a.grantor
 WHERE child.rolname IN ('postgres','whereto_plan_runtime')) m;
SELECT jsonb_build_object('fact','coverage','schema',n.nspname,'owner',pg_get_userbyid(n.nspowner),
 'acl',n.nspacl::text,'relations',(SELECT jsonb_agg(jsonb_build_array(c.relname,c.relkind,c.relrowsecurity,c.relforcerowsecurity) ORDER BY c.relname) FROM pg_class c WHERE c.relnamespace=n.oid),
 'application_routine_count',(SELECT count(*) FROM pg_proc p WHERE p.pronamespace=n.oid),
 'custom_nonrow_types',(SELECT count(*) FROM pg_type t WHERE t.typnamespace=n.oid AND t.typtype<>'c' AND t.typcategory<>'A'),
 'additional_financial_schemas',(SELECT count(*) FROM pg_namespace WHERE nspname IN ('provider_state','provider_rules','private_runtime','provider_witness')))
 FROM pg_namespace n WHERE nspname='whereto';
-- Unapproved external dependencies are a STOP gate, not permission to expand dump.
WITH app_objects AS (
 SELECT 'pg_class'::regclass::oid AS classid,c.oid AS objid FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='whereto'
 UNION SELECT 'pg_constraint'::regclass::oid,k.oid FROM pg_constraint k JOIN pg_namespace n ON n.oid=k.connamespace WHERE n.nspname='whereto'
 UNION SELECT 'pg_attrdef'::regclass::oid,a.oid FROM pg_attrdef a JOIN pg_class c ON c.oid=a.adrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='whereto'
 UNION SELECT 'pg_trigger'::regclass::oid,t.oid FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='whereto'
 UNION SELECT 'pg_policy'::regclass::oid,p.oid FROM pg_policy p JOIN pg_class c ON c.oid=p.polrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='whereto'
 UNION SELECT 'pg_proc'::regclass::oid,p.oid FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='whereto'
 UNION SELECT 'pg_type'::regclass::oid,t.oid FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace WHERE n.nspname='whereto'
), deps AS (
 SELECT DISTINCT o.type,o.schema,o.identity FROM app_objects a JOIN pg_depend d ON d.classid=a.classid AND d.objid=a.objid
 CROSS JOIN LATERAL pg_identify_object(d.refclassid,d.refobjid,d.refobjsubid) o
 WHERE o.schema IS NOT NULL AND o.schema NOT IN ('whereto','pg_catalog')
)
SELECT jsonb_build_object('fact','external_dependencies','dependencies',coalesce(jsonb_agg(to_jsonb(deps) ORDER BY schema,identity),'[]'::jsonb)) FROM deps;
-- Fingerprint selected application schema metadata, including policies/triggers.
WITH metadata AS (
 SELECT 'relation' AS kind,c.relname AS identity,jsonb_build_array(c.relkind,pg_get_userbyid(c.relowner),CASE WHEN c.relkind IN ('r','p','v','m','f','S') THEN (SELECT jsonb_agg(jsonb_build_array(pg_get_userbyid(a.grantor),CASE WHEN a.grantee=0 THEN 'PUBLIC' ELSE pg_get_userbyid(a.grantee) END,a.privilege_type,a.is_grantable) ORDER BY pg_get_userbyid(a.grantor),CASE WHEN a.grantee=0 THEN 'PUBLIC' ELSE pg_get_userbyid(a.grantee) END,a.privilege_type,a.is_grantable) FROM aclexplode(coalesce(c.relacl,acldefault(CASE WHEN c.relkind='S' THEN 's'::"char" ELSE 'r'::"char" END,c.relowner))) a) ELSE NULL END,c.relrowsecurity,c.relforcerowsecurity) AS value
 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='whereto'
 UNION ALL SELECT 'index',c.relname,to_jsonb(pg_get_indexdef(c.oid)) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='whereto' AND c.relkind IN ('i','I')
 UNION ALL SELECT 'column',c.relname||'.'||a.attnum,jsonb_build_array(a.attname,format_type(a.atttypid,a.atttypmod),a.attnotnull,a.attidentity,pg_get_expr(d.adbin,d.adrelid)) FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace LEFT JOIN pg_attrdef d ON d.adrelid=c.oid AND d.adnum=a.attnum WHERE n.nspname='whereto' AND a.attnum>0 AND NOT a.attisdropped
 UNION ALL SELECT 'constraint',c.relname||'.'||k.conname,to_jsonb(pg_get_constraintdef(k.oid)) FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='whereto'
 UNION ALL SELECT 'policy',c.relname||'.'||p.polname,jsonb_build_array(p.polcmd,p.polpermissive,ARRAY(SELECT CASE WHEN x=0 THEN 'PUBLIC' ELSE pg_get_userbyid(x) END FROM unnest(p.polroles) x ORDER BY 1),pg_get_expr(p.polqual,p.polrelid),pg_get_expr(p.polwithcheck,p.polrelid)) FROM pg_policy p JOIN pg_class c ON c.oid=p.polrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='whereto'
 UNION ALL SELECT 'trigger',c.relname||'.'||t.tgname,to_jsonb(pg_get_triggerdef(t.oid)) FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='whereto' AND NOT t.tgisinternal
 UNION ALL SELECT 'default_acl',pg_get_userbyid(a.defaclrole)||'.'||a.defaclobjtype::text,to_jsonb(a.defaclacl::text) FROM pg_default_acl a JOIN pg_namespace n ON n.oid=a.defaclnamespace WHERE n.nspname='whereto'
)
SELECT jsonb_build_object('fact','schema_fingerprint','sha256',encode(sha256(convert_to(coalesce(jsonb_agg(to_jsonb(metadata) ORDER BY kind,identity)::text,'[]'),'UTF8')),'hex')) FROM metadata;
-- Order by fixed-length row hashes; no source rows leave PostgreSQL here.
SELECT jsonb_build_object('fact','table','name','plans','count',count(*),'sha256',encode(sha256(convert_to(coalesce(string_agg(h,'' ORDER BY h),''),'UTF8')),'hex')) FROM (SELECT encode(sha256(convert_to(to_jsonb(t)::text,'UTF8')),'hex') h FROM whereto.plans t) s;
SELECT jsonb_build_object('fact','table','name','plan_constraints','count',count(*),'sha256',encode(sha256(convert_to(coalesce(string_agg(h,'' ORDER BY h),''),'UTF8')),'hex')) FROM (SELECT encode(sha256(convert_to(to_jsonb(t)::text,'UTF8')),'hex') h FROM whereto.plan_constraints t) s;
SELECT jsonb_build_object('fact','table','name','generated_itineraries','count',count(*),'sha256',encode(sha256(convert_to(coalesce(string_agg(h,'' ORDER BY h),''),'UTF8')),'hex')) FROM (SELECT encode(sha256(convert_to(to_jsonb(t)::text,'UTF8')),'hex') h FROM whereto.generated_itineraries t) s;
SELECT jsonb_build_object('fact','table','name','itinerary_stops','count',count(*),'sha256',encode(sha256(convert_to(coalesce(string_agg(h,'' ORDER BY h),''),'UTF8')),'hex')) FROM (SELECT encode(sha256(convert_to(to_jsonb(t)::text,'UTF8')),'hex') h FROM whereto.itinerary_stops t) s;
SELECT jsonb_build_object('fact','table','name','source_metadata','count',count(*),'sha256',encode(sha256(convert_to(coalesce(string_agg(h,'' ORDER BY h),''),'UTF8')),'hex')) FROM (SELECT encode(sha256(convert_to(to_jsonb(t)::text,'UTF8')),'hex') h FROM whereto.source_metadata t) s;
SELECT jsonb_build_object('fact','table','name','schema_migrations','count',count(*),'sha256',encode(sha256(convert_to(coalesce(string_agg(h,'' ORDER BY h),''),'UTF8')),'hex')) FROM (SELECT encode(sha256(convert_to(to_jsonb(t)::text,'UTF8')),'hex') h FROM whereto.schema_migrations t) s;
ROLLBACK;
