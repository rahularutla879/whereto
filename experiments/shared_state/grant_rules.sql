-- Shared pure pricing/limit rules installed separately in both fictional databases.
CREATE SCHEMA grant_rules;
REVOKE ALL ON SCHEMA grant_rules FROM PUBLIC;
CREATE TABLE grant_rules.configuration(id int PRIMARY KEY CHECK(id=1), grant_doc jsonb NOT NULL, rates jsonb NOT NULL);
CREATE TABLE grant_rules.test_clock(id int PRIMARY KEY CHECK(id=1), value timestamptz, last_seen timestamptz);
INSERT INTO grant_rules.test_clock VALUES(1,NULL,NULL);
CREATE FUNCTION grant_rules.immutable() RETURNS trigger LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$ BEGIN RAISE EXCEPTION 'immutable'; END $$;
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON grant_rules.configuration FOR EACH ROW EXECUTE FUNCTION grant_rules.immutable();
CREATE FUNCTION grant_rules.integer(v jsonb,hi numeric) RETURNS boolean LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
 SELECT coalesce(jsonb_typeof(v)='number' AND v::text ~ '^[0-9]{1,13}$' AND (v::text)::numeric BETWEEN 0 AND hi,false)
$$;
CREATE FUNCTION grant_rules.now_at() RETURNS timestamptz LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
DECLARE t timestamptz; previous timestamptz;
BEGIN
 SELECT coalesce(value,clock_timestamp()),last_seen INTO STRICT t,previous FROM grant_rules.test_clock WHERE id=1 FOR UPDATE;
 IF t<previous THEN RAISE EXCEPTION 'clock_rollback'; END IF;
 UPDATE grant_rules.test_clock SET last_seen=t WHERE id=1;
 RETURN t;
END $$;
CREATE FUNCTION grant_rules.validate(g jsonb,r jsonb) RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
DECLARE k text; n int; x jsonb;
BEGIN
 IF jsonb_typeof(g) IS DISTINCT FROM 'object' OR (SELECT count(*) FROM jsonb_object_keys(g))<>13
 OR NOT(g ?& ARRAY['id','version','epoch','total','daily','outing','providers','timezone','expires','roots','attempts','concurrency','domain'])
 OR g->>'version' IS DISTINCT FROM 'synthetic-app-grant-v1' OR g->>'domain' IS DISTINCT FROM 'synthetic-application-domain-v1'
 OR coalesce(g->>'epoch','') !~ '^[0-9a-f]{64}$' OR (g->>'id')::uuid IS NULL
 OR NOT EXISTS(SELECT 1 FROM pg_timezone_names WHERE name=g->>'timezone')
 OR (g->>'expires')::timestamptz IS NULL OR jsonb_typeof(g->'roots') IS DISTINCT FROM 'array'
 OR jsonb_array_length(g->'roots') NOT BETWEEN 1 AND 16 THEN RAISE EXCEPTION 'grant_configuration'; END IF;
 FOREACH k IN ARRAY ARRAY['total','daily','outing','attempts','concurrency'] LOOP
   IF NOT grant_rules.integer(g->k,1000000000000) THEN RAISE EXCEPTION 'grant_bound'; END IF;
 END LOOP;
 IF (g->>'concurrency')::int NOT BETWEEN 1 AND 16 OR (g->>'attempts')::numeric>1000000
 OR (g->>'daily')::numeric>(g->>'total')::numeric OR (g->>'outing')::numeric>(g->>'total')::numeric
 OR jsonb_typeof(g->'providers') IS DISTINCT FROM 'object' OR (SELECT count(*) FROM jsonb_object_keys(g->'providers'))<>3
 OR NOT(g->'providers' ?& ARRAY['synthetic_maps','fictional_llm_a','fictional_llm_b'])
 THEN RAISE EXCEPTION 'grant_bound'; END IF;
 FOR k,x IN SELECT * FROM jsonb_each(g->'providers') LOOP
   IF NOT grant_rules.integer(x,(g->>'total')::numeric) THEN RAISE EXCEPTION 'provider_bound'; END IF;
 END LOOP;
 FOR x IN SELECT * FROM jsonb_array_elements(g->'roots') LOOP PERFORM (x#>>'{}')::uuid; END LOOP;
 SELECT count(DISTINCT value) INTO n FROM jsonb_array_elements(g->'roots');
 IF n<>jsonb_array_length(g->'roots') OR jsonb_typeof(r) IS DISTINCT FROM 'object' OR NOT(r ?& ARRAY['maps','models'])
 OR r->'maps' IS DISTINCT FROM '{"search_pro":32000,"search_enterprise":35000,"details":20000,"details_pro":17000,"matrix_element":5000,"matrix_pro_element":10000}'::jsonb
 THEN RAISE EXCEPTION 'grant_rates'; END IF;
END $$;
CREATE FUNCTION grant_rules.price(lines jsonb,rates jsonb) RETURNS bigint LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
DECLARE line jsonb; model jsonb; total numeric:=0; price numeric;
BEGIN
 IF jsonb_typeof(lines) IS DISTINCT FROM 'array' OR jsonb_array_length(lines) NOT BETWEEN 1 AND 64 THEN RAISE EXCEPTION 'priced_lines'; END IF;
 FOR line IN SELECT * FROM jsonb_array_elements(lines) LOOP
   IF line->>'kind'='maps' THEN
     IF (SELECT count(*) FROM jsonb_object_keys(line))<>5 OR NOT(line ?& ARRAY['kind','sku','units','rate_version','request_digest'])
     OR line->>'rate_version'<>'development_cost.RATES-2026-11-03-v1'
     OR NOT grant_rules.integer(line->'units',1000000000000)
     OR coalesce(line->>'request_digest','') !~ '^[0-9a-f]{64}$'
     OR jsonb_typeof(line->'sku') IS DISTINCT FROM 'string'
     OR (coalesce(line->>'sku','')<>'none' AND NOT(rates->'maps' ? (line->>'sku')))
     OR (line->>'sku'<>'none' AND NOT grant_rules.integer(rates->'maps'->(line->>'sku'),1000000)) THEN RAISE EXCEPTION 'maps_price'; END IF;
     price:=(line->>'units')::numeric*coalesce((rates->'maps'->>(line->>'sku'))::numeric,0);
   ELSIF line->>'kind'='llm' THEN
     model:=rates->'models'->(line->>'model');
     IF model IS NULL OR (SELECT count(*) FROM jsonb_object_keys(line))<>12
     OR NOT(line ?& ARRAY['kind','provider','model','rate_version','input_tokens','max_output','cached_tokens','reasoning_cap','tool_calls','prompt_hash','schema_hash','request_digest'])
     OR model->>'profile' IS DISTINCT FROM 'fake-utf8-complete-v1'
     OR coalesce(model->>'provider','') NOT IN ('fictional_llm_a','fictional_llm_b')
     OR NOT grant_rules.integer(model->'input_rate',1000000) OR NOT grant_rules.integer(model->'output_rate',1000000)
     OR NOT grant_rules.integer(model->'max_input',100000) OR NOT grant_rules.integer(model->'max_output',64)
     OR line->>'provider' IS DISTINCT FROM model->>'provider' OR line->>'rate_version' IS DISTINCT FROM model->>'rate_version'
     OR line->>'prompt_hash' IS DISTINCT FROM model->>'prompt_hash' OR line->>'schema_hash' IS DISTINCT FROM model->>'schema_hash'
     OR NOT grant_rules.integer(line->'input_tokens',(model->>'max_input')::numeric)
     OR NOT grant_rules.integer(line->'max_output',(model->>'max_output')::numeric)
     OR line->'cached_tokens' IS DISTINCT FROM '0'::jsonb OR line->'reasoning_cap' IS DISTINCT FROM '0'::jsonb
     OR line->'tool_calls' IS DISTINCT FROM '0'::jsonb OR coalesce(line->>'request_digest','') !~ '^[0-9a-f]{64}$'
     THEN RAISE EXCEPTION 'unbounded_or_unknown_llm_cost'; END IF;
     price:=(line->>'input_tokens')::numeric*(model->>'input_rate')::numeric+(line->>'max_output')::numeric*(model->>'output_rate')::numeric;
   ELSE RAISE EXCEPTION 'price_kind'; END IF;
   IF price IS NULL OR price<0 OR price<>trunc(price) OR total+price>1000000000000 THEN RAISE EXCEPTION 'price_overflow'; END IF;
   total:=total+price;
 END LOOP;
 RETURN total::bigint;
END $$;
CREATE FUNCTION grant_rules.check_limit(q jsonb,used_total numeric,used_provider numeric,used_day numeric,used_outing numeric,attempts bigint,active bigint) RETURNS void
LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
DECLARE g jsonb; price bigint; now_at timestamptz; rates jsonb;
BEGIN
 SELECT grant_doc,configuration.rates INTO STRICT g,rates FROM grant_rules.configuration WHERE id=1;
 PERFORM grant_rules.validate(g,rates);now_at:=grant_rules.now_at();price:=grant_rules.price(q->'lines',rates);
 IF q->>'grant' IS DISTINCT FROM g->>'id' OR q->>'version' IS DISTINCT FROM g->>'version'
 OR EXISTS(SELECT 1 FROM jsonb_array_elements(q->'lines') l WHERE q->>'provider' IS DISTINCT FROM CASE WHEN l->>'kind'='maps' THEN 'synthetic_maps' ELSE l->>'provider' END)
 OR q->>'epoch' IS DISTINCT FROM g->>'epoch' OR q->>'provider' IS NULL OR NOT(g->'providers' ? (q->>'provider'))
 OR NOT(g->'roots' @> jsonb_build_array(q->>'root')) OR (q->>'outing')::uuid IS NULL
 OR (q->>'charge')::numeric IS DISTINCT FROM price OR now_at>=(g->>'expires')::timestamptz
 OR q->>'day' IS DISTINCT FROM ((now_at AT TIME ZONE (g->>'timezone'))::date)::text
 OR used_total+price>(g->>'total')::numeric OR used_provider+price>(g->'providers'->>(q->>'provider'))::numeric
 OR used_day+price>(g->>'daily')::numeric OR used_outing+price>(g->>'outing')::numeric
 OR attempts+1>(g->>'attempts')::bigint OR active>=(g->>'concurrency')::bigint THEN RAISE EXCEPTION 'grant_limit_or_identity'; END IF;
END $$;
REVOKE ALL ON ALL TABLES IN SCHEMA grant_rules FROM PUBLIC;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA grant_rules FROM PUBLIC;
