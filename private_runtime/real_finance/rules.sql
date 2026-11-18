-- Installed only into this separately versioned profile, in BOTH databases.
-- No configuration/grant is inserted. Only the separately trusted owner may enroll.
CREATE OR REPLACE FUNCTION provider_rules.validate(g jsonb,r jsonb) RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
DECLARE k text;x jsonb;m jsonb;
BEGIN
 IF jsonb_typeof(g) IS DISTINCT FROM 'object' OR (SELECT count(*) FROM jsonb_object_keys(g))<>14
 OR NOT(g ?& ARRAY['id','version','epoch','total','daily','outing','session','providers','timezone','expires','roots','attempts','concurrency','domain'])
 OR g->>'version' IS DISTINCT FROM 'real-app-grant-v1' OR g->>'domain' IS DISTINCT FROM 'whereto-real-providers-v1'
 OR coalesce(g->>'epoch','') !~ '^[0-9a-f]{64}$' OR (g->>'id')::uuid IS NULL
 OR NOT EXISTS(SELECT 1 FROM pg_timezone_names WHERE name=g->>'timezone')
 OR (g->>'expires')::timestamptz IS NULL OR jsonb_typeof(g->'roots') IS DISTINCT FROM 'array'
 OR jsonb_array_length(g->'roots') NOT BETWEEN 1 AND 16 THEN RAISE EXCEPTION 'real_grant_configuration'; END IF;
 FOREACH k IN ARRAY ARRAY['total','daily','outing','session','attempts','concurrency'] LOOP
 IF NOT provider_rules.integer(g->k,1000000000000) THEN RAISE EXCEPTION 'real_grant_bound'; END IF; END LOOP;
 IF (g->>'concurrency')::int NOT BETWEEN 1 AND 16 OR (g->>'attempts')::numeric>1000000
 OR (g->>'session')::numeric>(g->>'total')::numeric
 OR (g->>'daily')::numeric>(g->>'total')::numeric OR (g->>'outing')::numeric>(g->>'total')::numeric
 OR jsonb_typeof(g->'providers') IS DISTINCT FROM 'object' OR (SELECT count(*) FROM jsonb_object_keys(g->'providers'))<>2
 OR NOT(g->'providers' ?& ARRAY['google','openai']) THEN RAISE EXCEPTION 'real_provider_bound'; END IF;
 FOR k,x IN SELECT * FROM jsonb_each(g->'providers') LOOP
 IF NOT provider_rules.integer(x,(g->>'total')::numeric) THEN RAISE EXCEPTION 'real_provider_bound'; END IF; END LOOP;
 FOR x IN SELECT * FROM jsonb_array_elements(g->'roots') LOOP IF jsonb_typeof(x) IS DISTINCT FROM 'string' OR (x#>>'{}')::uuid IS NULL THEN RAISE EXCEPTION 'real_root_identity'; END IF; END LOOP;
 IF (SELECT count(DISTINCT value) FROM jsonb_array_elements(g->'roots'))<>jsonb_array_length(g->'roots') THEN RAISE EXCEPTION 'real_roots'; END IF;
 IF jsonb_typeof(r) IS DISTINCT FROM 'object' OR (SELECT count(*) FROM jsonb_object_keys(r))<>11
 OR NOT(r ?& ARRAY['version','checked','expires','price_evidence','qualification_evidence','count_fee_evidence','count_fee','google_account','maps','models','currency'])
 OR coalesce(r->>'version','') !~ '^[a-zA-Z0-9_.:-]{1,128}$' OR r->>'currency' IS DISTINCT FROM 'USD'
 OR coalesce(r->>'price_evidence','') !~ '^[0-9a-f]{64}$' OR coalesce(r->>'qualification_evidence','') !~ '^[0-9a-f]{64}$'
 OR coalesce(r->>'count_fee_evidence','') !~ '^[0-9a-f]{64}$' OR r->'count_fee' IS DISTINCT FROM '0'::jsonb
 OR coalesce(r->>'google_account','') !~ '^[a-z][a-z0-9-]{5,62}$'
 OR jsonb_typeof(r->'maps') IS DISTINCT FROM 'object' OR (SELECT count(*) FROM jsonb_object_keys(r->'maps'))<>3
 OR NOT(r->'maps' ?& ARRAY['search_pro','matrix_element','matrix_pro_element'])
 OR jsonb_typeof(r->'models') IS DISTINCT FROM 'object' OR (SELECT count(*) FROM jsonb_object_keys(r->'models'))<>1
 OR NOT(r->'models' ? 'gpt-6-luna') THEN RAISE EXCEPTION 'real_prices_missing_or_unknown_category'; END IF;
 IF NOT provider_rules.integer(r->'checked',9007199254740991) OR NOT provider_rules.integer(r->'expires',9007199254740991)
 OR (r->>'expires')::numeric<=(r->>'checked')::numeric OR (r->>'expires')::numeric-(r->>'checked')::numeric>86400 THEN RAISE EXCEPTION 'real_price_window'; END IF;
 FOR k,x IN SELECT * FROM jsonb_each(r->'maps') LOOP
 IF NOT provider_rules.integer(x,1000000) OR x='0'::jsonb THEN RAISE EXCEPTION 'real_maps_rate'; END IF; END LOOP;
 m:=r->'models'->'gpt-6-luna';
 IF jsonb_typeof(m) IS DISTINCT FROM 'object' OR (SELECT count(*) FROM jsonb_object_keys(m))<>13
 OR NOT(m ?& ARRAY['account','revision','profile','input_ppm','cache_write_ppm','output_ppm','extra_fee','max_input','max_output','margin','template','counter_version','count_ttl'])
 OR coalesce(m->>'account','') !~ '^proj_[A-Za-z0-9]{8,80}$' OR m->>'account'='proj_E4EfEvC5uQYN4nqFaYZoo3I4'
 OR coalesce(m->>'revision','') !~ '^[A-Za-z0-9_.:-]{1,128}$'
 OR m->>'profile' IS DISTINCT FROM 'openai-full-input-cache-write-output-v1'
 OR m->>'counter_version' IS DISTINCT FROM 'openai-complete-count-v1'
 OR NOT provider_rules.integer(m->'input_ppm',1000000000000) OR NOT provider_rules.integer(m->'cache_write_ppm',1000000000000)
 OR NOT provider_rules.integer(m->'output_ppm',1000000000000) OR m->'extra_fee' IS DISTINCT FROM '0'::jsonb
 OR NOT provider_rules.integer(m->'max_input',100000) OR (m->>'max_input')::int<1
 OR NOT provider_rules.integer(m->'margin',100000) OR (m->>'margin')::int>=(m->>'max_input')::int
 OR NOT provider_rules.integer(m->'max_output',2000) OR (m->>'max_output')::int<1
 OR NOT provider_rules.integer(m->'count_ttl',600) OR (m->>'count_ttl')::int<1
 OR jsonb_typeof(m->'template') IS DISTINCT FROM 'object' OR (SELECT count(*) FROM jsonb_object_keys(m->'template'))<>8
 OR NOT(m->'template' ?& ARRAY['model','input','temperature','reasoning','service_tier','max_output_tokens','store','text'])
 OR m->'template'->>'model' IS DISTINCT FROM 'gpt-6-luna' OR m->'template'->'reasoning' IS DISTINCT FROM '{"effort":"none"}'::jsonb
 OR m->'template'->>'service_tier' IS DISTINCT FROM 'default' OR m->'template'->'store' IS DISTINCT FROM 'false'::jsonb
 OR m->'template'#>>'{input,-1,content}' IS DISTINCT FROM ''
 OR m->'template'#>>'{input,-1,role}' IS DISTINCT FROM 'user'
 OR m->'template'#>>'{text,format,type}' IS DISTINCT FROM 'json_schema'
 OR NOT provider_rules.integer(m->'template'->'max_output_tokens',(m->>'max_output')::numeric) OR (m->'template'->>'max_output_tokens')::int<1
 THEN RAISE EXCEPTION 'real_model_policy'; END IF;
END $$;
CREATE FUNCTION provider_rules.current_rates() RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
DECLARE g jsonb;r jsonb;t numeric;
BEGIN
 SELECT grant_doc,rates INTO STRICT g,r FROM provider_rules.configuration WHERE id=1;
 t:=extract(epoch FROM provider_rules.now_at());
 IF t<(r->>'checked')::numeric OR t>=(r->>'expires')::numeric
 THEN RAISE EXCEPTION 'real_stale_prices'; END IF;
 RETURN r;
END $$;
CREATE OR REPLACE FUNCTION provider_rules.price(lines jsonb,rates jsonb) RETURNS bigint LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
DECLARE l jsonb;m jsonb;total numeric:=0;price numeric;b numeric;
BEGIN
 IF rates IS DISTINCT FROM provider_rules.current_rates() OR jsonb_typeof(lines) IS DISTINCT FROM 'array' OR jsonb_array_length(lines) NOT BETWEEN 1 AND 64 THEN RAISE EXCEPTION 'real_priced_lines'; END IF;
 FOR l IN SELECT * FROM jsonb_array_elements(lines) LOOP
 IF l->>'rate_version' IS DISTINCT FROM rates->>'version' OR coalesce(l->>'request_digest','') !~ '^[0-9a-f]{64}$' THEN RAISE EXCEPTION 'real_rate_binding'; END IF;
 m:=rates->'models'->'gpt-6-luna';
 IF l->>'kind'='maps' THEN
 IF (SELECT count(*) FROM jsonb_object_keys(l))<>5 OR NOT(l ?& ARRAY['kind','sku','units','rate_version','request_digest'])
 OR NOT(rates->'maps' ? coalesce(l->>'sku','')) OR NOT provider_rules.integer(l->'units',300) OR (l->>'units')::int<1
 OR (l->>'sku'='search_pro' AND l->'units' IS DISTINCT FROM '1'::jsonb) THEN RAISE EXCEPTION 'real_maps_units'; END IF;
 price:=(l->>'units')::numeric*(rates->'maps'->>(l->>'sku'))::numeric;
 ELSIF l->>'kind'='count' THEN
 IF (SELECT count(*) FROM jsonb_object_keys(l))<>8 OR NOT(l ?& ARRAY['kind','rate_version','request_digest','count_digest','model','model_revision','account','units'])
 OR l->'units' IS DISTINCT FROM '1'::jsonb OR l->>'model' IS DISTINCT FROM 'gpt-6-luna' OR l->>'model_revision' IS DISTINCT FROM m->>'revision'
 OR l->>'account' IS DISTINCT FROM m->>'account' OR coalesce(l->>'count_digest','') !~ '^[0-9a-f]{64}$' THEN RAISE EXCEPTION 'real_count_price'; END IF;
 price:=0; -- Only the explicitly enrolled zero-fee count contract is supported.
 ELSIF l->>'kind'='llm' THEN
 IF (SELECT count(*) FROM jsonb_object_keys(l))<>14 OR NOT(l ?& ARRAY['kind','provider','model','model_revision','account','rate_version','input_tokens','max_output','cached_tokens','reasoning_cap','tool_calls','prompt_hash','schema_hash','request_digest'])
 OR l->>'provider' IS DISTINCT FROM 'openai' OR l->>'model' IS DISTINCT FROM 'gpt-6-luna'
 OR l->>'account' IS DISTINCT FROM m->>'account' OR l->>'model_revision' IS DISTINCT FROM m->>'revision'
 OR l->>'prompt_hash' IS DISTINCT FROM encode(sha256(convert_to((m->'template'->'input'->0)::text,'UTF8')),'hex')
 OR l->>'schema_hash' IS DISTINCT FROM encode(sha256(convert_to((m->'template'#>'{text,format,schema}')::text,'UTF8')),'hex')
 OR NOT provider_rules.integer(l->'input_tokens',(m->>'max_input')::numeric) OR (l->>'input_tokens')::bigint<1
 OR NOT provider_rules.integer(l->'max_output',(m->>'max_output')::numeric) OR (l->>'max_output')::bigint<1
 OR l->'cached_tokens' IS DISTINCT FROM '0'::jsonb OR l->'reasoning_cap' IS DISTINCT FROM '0'::jsonb OR l->'tool_calls' IS DISTINCT FROM '0'::jsonb THEN RAISE EXCEPTION 'real_llm_price'; END IF;
 b:=(l->>'input_tokens')::numeric;
 -- No assumed cache discount. Reserve FULL input plus worst-case cache writes,
 -- and all maximum output including invisible tokens. Round each category UP.
 price:=ceil(b*(m->>'input_ppm')::numeric/1000000)+ceil(b*(m->>'cache_write_ppm')::numeric/1000000)
       +ceil((l->>'max_output')::numeric*(m->>'output_ppm')::numeric/1000000);
 ELSE RAISE EXCEPTION 'real_unknown_price_category'; END IF;
 IF price IS NULL OR price<0 OR total+price>1000000000000 THEN RAISE EXCEPTION 'real_price_overflow'; END IF;
 total:=total+price;
 END LOOP;
 RETURN total::bigint;
END $$;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA provider_rules FROM PUBLIC;

-- Validate every INSERT, even if an operator forgets the explicit review check.
-- The parent's immutable UPDATE/DELETE trigger and no table privileges preserve
-- this invariant; only the trusted schema owner could disable these protections.
CREATE FUNCTION provider_rules.enrollment_guard() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
BEGIN PERFORM provider_rules.validate(NEW.grant_doc,NEW.rates);RETURN NEW;END $$;
CREATE TRIGGER validated_enrollment BEFORE INSERT ON provider_rules.configuration FOR EACH ROW EXECUTE FUNCTION provider_rules.enrollment_guard();
REVOKE ALL ON FUNCTION provider_rules.enrollment_guard() FROM PUBLIC;
CREATE FUNCTION provider_rules.reported_bound(spec jsonb,report jsonb,rates jsonb) RETURNS bigint LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
DECLARE m jsonb;
BEGIN
 IF rates IS DISTINCT FROM provider_rules.current_rates() THEN RAISE EXCEPTION 'real_report_rate'; END IF;
 m:=rates->'models'->(spec->>'model');
 -- Informational conservative arithmetic only. NO refund/release/authorization.
 RETURN (ceil((report->>'input_tokens')::numeric*(m->>'input_ppm')::numeric/1000000)
       +ceil((report->>'cache_write_tokens')::numeric*(m->>'cache_write_ppm')::numeric/1000000)
       +ceil((report->>'output_tokens')::numeric*(m->>'output_ppm')::numeric/1000000))::bigint;
END $$;
REVOKE ALL ON FUNCTION provider_rules.reported_bound(jsonb,jsonb,jsonb) FROM PUBLIC;
