-- Additive facts in the SAME grant/witness history. No grants/policies installed.
CREATE TABLE provider_state.real_sources(capability text PRIMARY KEY REFERENCES provider_state.capabilities(id), session text NOT NULL,revision bigint NOT NULL,worker uuid NOT NULL,fence bigint NOT NULL,source_digest text NOT NULL,commitment text NOT NULL,request_digest text NOT NULL,count_digest text NOT NULL,http text NOT NULL,inference text NOT NULL);
CREATE TABLE provider_state.count_attempts(operation uuid PRIMARY KEY,capability text UNIQUE NOT NULL REFERENCES provider_state.real_sources(capability),quote jsonb NOT NULL);
CREATE TABLE provider_state.count_intents(operation uuid PRIMARY KEY REFERENCES provider_state.count_attempts(operation),quote jsonb NOT NULL);
CREATE TABLE provider_state.count_results(operation uuid PRIMARY KEY REFERENCES provider_state.count_intents(operation),measured bigint NOT NULL CHECK(measured>0),bound bigint NOT NULL CHECK(bound>=measured),response_digest text NOT NULL,expires timestamptz NOT NULL);
CREATE TABLE provider_state.count_outcomes(operation uuid PRIMARY KEY REFERENCES provider_state.count_intents(operation),state text NOT NULL CHECK(state IN ('SUCCEEDED','UNCERTAIN')));
DO $$DECLARE t text;BEGIN FOREACH t IN ARRAY ARRAY['real_sources','count_attempts','count_intents','count_results','count_outcomes'] LOOP
 EXECUTE format('CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON provider_state.%I FOR EACH ROW EXECUTE FUNCTION provider_state.immutable()',t);END LOOP;END $$;
CREATE FUNCTION provider_state.real_source_current(cap text) RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
DECLARE src provider_state.real_sources%ROWTYPE;r jsonb;meta jsonb;
BEGIN
 PERFORM provider_state.finance_guard();r:=provider_rules.current_rates();
 SELECT * INTO STRICT src FROM provider_state.real_sources WHERE capability=cap;
 meta:=provider_state.evidence_protocol('evidence_meta',jsonb_build_object('session',src.session,'revision',src.revision,'worker',src.worker,'fence',src.fence),'real',(SELECT grant_doc->>'epoch' FROM provider_rules.configuration),NULL);
 IF meta#>>'{anchor,commitment}' IS DISTINCT FROM src.commitment OR meta#>>'{anchor,environment}' IS DISTINCT FROM 'real' OR meta#>>'{anchor,epoch}' IS DISTINCT FROM (SELECT grant_doc->>'epoch' FROM provider_rules.configuration) OR NOT EXISTS(SELECT 1 FROM provider_state.admission_leases WHERE id=src.http AND domain='http' AND refs>0 AND worker=src.worker)
 OR NOT EXISTS(SELECT 1 FROM provider_state.admission_leases WHERE id=src.inference AND domain='inference' AND refs>0 AND worker=src.worker AND fingerprint=src.source_digest)
 OR EXISTS(SELECT 1 FROM provider_state.operations WHERE capability=cap)
 OR provider_rules.now_at()>=(SELECT (grant_doc->>'expires')::timestamptz FROM provider_rules.configuration) THEN RAISE EXCEPTION 'real_source_admission'; END IF;
 RETURN r;
END $$;
CREATE FUNCTION provider_state.real_enroll_request(cap text,source bytea,wire bytea,projection bytea) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE c provider_state.capabilities%ROWTYPE;s provider_state.sessions%ROWTYPE;b provider_state.bridge_actions%ROWTYPE;r jsonb;m jsonb;v jsonb;src jsonb;
BEGIN
 PERFORM provider_state.finance_guard();r:=provider_rules.current_rates();m:=r#>'{models,gpt-6-luna}';
 SELECT * INTO STRICT c FROM provider_state.capabilities WHERE id=cap;
 SELECT * INTO STRICT s FROM provider_state.sessions WHERE id=c.session;
 SELECT * INTO STRICT b FROM provider_state.bridge_actions WHERE session=s.id;
 IF octet_length(source)>65536 OR octet_length(wire)>100000 OR octet_length(projection)>100000
 OR NOT(convert_from(wire,'UTF8') IS JSON OBJECT WITH UNIQUE KEYS) OR NOT(convert_from(source,'UTF8') IS JSON OBJECT WITH UNIQUE KEYS)
 OR NOT(convert_from(projection,'UTF8') IS JSON OBJECT WITH UNIQUE KEYS) THEN RAISE EXCEPTION 'real_request_encoding'; END IF;
 v:=convert_from(wire,'UTF8')::jsonb;src:=convert_from(source,'UTF8')::jsonb;
 IF c.purpose<>'provider_action' OR c.revision<>s.revision OR s.revoked OR s.expires<=provider_state.protocol_now()
 OR b.source_digest IS DISTINCT FROM encode(sha256(source),'hex') OR src->>'text' IS NULL OR length(src->>'text') NOT BETWEEN 1 AND 6000
 OR (src->'pending' IS NOT NULL AND src->'pending'<>'null'::jsonb)
 OR v#>>'{input,-1,content}' IS DISTINCT FROM src->>'text'
 OR jsonb_set(v,'{input,-1,content}','""'::jsonb) IS DISTINCT FROM m->'template'
 OR convert_from(projection,'UTF8')::jsonb IS DISTINCT FROM jsonb_build_object('model',v->'model','input',v->'input','text',v->'text','reasoning',v->'reasoning')
 OR NOT EXISTS(SELECT 1 FROM provider_state.app_sources WHERE inference=b.inference_id AND source_digest=b.source_digest)
 THEN RAISE EXCEPTION 'real_source_request_binding'; END IF;
 INSERT INTO provider_state.real_sources VALUES(cap,s.id,s.revision,s.worker,s.fence,b.source_digest,(SELECT commitment FROM provider_state.evidence_anchors WHERE session=s.id),encode(sha256(wire),'hex'),encode(sha256(projection),'hex'),b.http_id,b.inference_id);
 PERFORM provider_state.real_source_current(cap);
END $$;
CREATE FUNCTION provider_state.real_count_quote(cap text,wire bytea,projection bytea,op uuid) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE r jsonb;m jsonb;src provider_state.real_sources%ROWTYPE;g jsonb;b record;q jsonb;line jsonb;settings jsonb;
BEGIN
 r:=provider_state.real_source_current(cap);m:=r#>'{models,gpt-6-luna}';SELECT * INTO STRICT src FROM provider_state.real_sources WHERE capability=cap;
 IF encode(sha256(wire),'hex')<>src.request_digest OR encode(sha256(projection),'hex')<>src.count_digest THEN RAISE EXCEPTION 'real_counter_payload'; END IF;
 SELECT grant_doc INTO STRICT g FROM provider_rules.configuration WHERE id=1;
 SELECT o.id AS outing,o.root INTO STRICT b FROM provider_state.budget_bindings bb JOIN provider_state.budget_outings o ON o.id=bb.outing WHERE bb.session=src.session;
 SELECT p.settings INTO STRICT settings FROM provider_state.finance_policy p WHERE id=1;
 IF (SELECT count(*) FROM provider_state.count_attempts WHERE quote->>'root'=b.root::text)+(SELECT count(*) FROM provider_state.financial_lines WHERE root=b.root)+1>(settings->>'requests_per_session')::int
 OR (SELECT count(*) FROM provider_state.count_attempts WHERE quote->>'outing'=b.outing::text)+(SELECT count(*) FROM provider_state.financial_lines WHERE outing=b.outing)+1>(settings->>'requests_per_outing')::int THEN RAISE EXCEPTION 'real_counter_quantity'; END IF;
 line:=jsonb_build_object('kind','count','rate_version',r->>'version','request_digest',src.request_digest,'count_digest',src.count_digest,'model','gpt-6-luna','model_revision',m->>'revision','account',m->>'account','units',1);
 PERFORM provider_rules.price(jsonb_build_array(line),r);
 q:=jsonb_build_object('operation',op,'session',src.session,'capability',cap,'revision',src.revision,'fence',src.fence,'worker',src.worker,
 'grant',g->>'id','version',g->>'version','epoch',g->>'epoch','provider','openai','account',m->>'account','policy',encode(sha256(convert_to(r::text,'UTF8')),'hex'),'root',b.root,'outing',b.outing,
 'day',(provider_rules.now_at() AT TIME ZONE (g->>'timezone'))::date,'charge',0,'lines',jsonb_build_array(line));
 INSERT INTO provider_state.count_attempts VALUES(op,cap,q);RETURN q;
END $$;
CREATE FUNCTION provider_state.real_count_phase(op uuid,phase text) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE a provider_state.count_attempts%ROWTYPE;id text;r jsonb;
BEGIN
 SELECT * INTO STRICT a FROM provider_state.count_attempts WHERE operation=op;
 r:=provider_state.real_source_current(a.capability);
 IF a.quote->>'policy' IS DISTINCT FROM encode(sha256(convert_to(r::text,'UTF8')),'hex') OR a.quote->>'epoch' IS DISTINCT FROM (SELECT grant_doc->>'epoch' FROM provider_rules.configuration) THEN RAISE EXCEPTION 'real_counter_policy'; END IF;
 IF phase='reserve' THEN INSERT INTO provider_state.count_intents VALUES(op,a.quote);
 ELSIF phase IN ('dispatch','deliver') THEN
 IF NOT EXISTS(SELECT 1 FROM provider_state.count_intents WHERE operation=op) OR NOT EXISTS(SELECT 1 FROM provider_state.app_witness_facts f WHERE f.id=(CASE phase WHEN 'dispatch' THEN 'reserve:' ELSE 'dispatch:' END)||op::text||(CASE phase WHEN 'dispatch' THEN '' ELSE ':1' END)) THEN RAISE EXCEPTION 'real_counter_order'; END IF;
 ELSE RAISE EXCEPTION 'real_counter_phase'; END IF;
 id:=phase||':'||op::text||CASE phase WHEN 'reserve' THEN '' ELSE ':1' END;
 INSERT INTO provider_state.app_witness_facts VALUES(id,a.quote);RETURN a.quote;
END $$;
CREATE FUNCTION provider_state.real_count_commit(op uuid,measured bigint,raw bytea) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE a provider_state.count_attempts%ROWTYPE;r jsonb;m jsonb;v jsonb;bounded bigint;
BEGIN
 SELECT * INTO STRICT a FROM provider_state.count_attempts WHERE operation=op;r:=provider_state.real_source_current(a.capability);m:=r#>'{models,gpt-6-luna}';
 IF a.quote->>'policy' IS DISTINCT FROM encode(sha256(convert_to(r::text,'UTF8')),'hex') OR NOT EXISTS(SELECT 1 FROM provider_state.app_witness_facts WHERE id='deliver:'||op::text||':1') THEN RAISE EXCEPTION 'real_counter_intent'; END IF;
 IF octet_length(raw)>700000 OR NOT(convert_from(raw,'UTF8') IS JSON OBJECT WITH UNIQUE KEYS) THEN RAISE EXCEPTION 'real_count_response'; END IF;
 v:=convert_from(raw,'UTF8')::jsonb;
 IF (SELECT count(*) FROM jsonb_object_keys(v))<>2 OR v->>'object' IS DISTINCT FROM 'response.input_tokens'
 OR NOT provider_rules.integer(v->'input_tokens',(m->>'max_input')::numeric) OR v->'input_tokens' IS DISTINCT FROM to_jsonb(measured) OR measured<1 THEN RAISE EXCEPTION 'real_count_response'; END IF;
 bounded:=measured+(m->>'margin')::bigint;
 IF bounded>(m->>'max_input')::bigint THEN RAISE EXCEPTION 'real_input_bound'; END IF;
 INSERT INTO provider_state.token_counts VALUES(a.capability,a.quote#>>'{lines,0,request_digest}',bounded,'gpt-6-luna',(m->'template'->>'max_output_tokens')::bigint);
 INSERT INTO provider_state.count_results VALUES(op,measured,bounded,encode(sha256(raw),'hex'),least(provider_rules.now_at()+(m->>'count_ttl')::int*interval '1 second',to_timestamp((r->>'expires')::numeric),(SELECT expires FROM provider_state.sessions WHERE id=a.quote->>'session')));
END $$;
CREATE FUNCTION provider_state.real_count_finish(op uuid,state text) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE q jsonb;
BEGIN
 -- Still lock/read the core and retain facts even when the price window expired.
 PERFORM provider_state.protocol('snapshot','{}');SELECT quote INTO STRICT q FROM provider_state.count_intents WHERE operation=op;
 IF state NOT IN ('SUCCEEDED','UNCERTAIN') OR state IS NULL OR (state='SUCCEEDED' AND NOT EXISTS(SELECT 1 FROM provider_state.count_results WHERE operation=op)) THEN RAISE EXCEPTION 'real_count_terminal'; END IF;
 INSERT INTO provider_state.count_outcomes VALUES(op,state);
 INSERT INTO provider_state.app_witness_facts VALUES('outcome:'||op::text,q||jsonb_build_object('state',state));RETURN q;
END $$;
CREATE FUNCTION provider_state.real_count_fresh(cap text) RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
DECLARE r jsonb;a provider_state.count_attempts%ROWTYPE;c provider_state.count_results%ROWTYPE;
BEGIN
 r:=provider_rules.current_rates();SELECT * INTO STRICT a FROM provider_state.count_attempts WHERE capability=cap;SELECT * INTO STRICT c FROM provider_state.count_results WHERE operation=a.operation;
 IF c.expires<=provider_rules.now_at() OR a.quote->>'policy' IS DISTINCT FROM encode(sha256(convert_to(r::text,'UTF8')),'hex')
 OR NOT EXISTS(SELECT 1 FROM provider_state.count_outcomes WHERE operation=a.operation AND state='SUCCEEDED') THEN RAISE EXCEPTION 'real_count_stale'; END IF;
END $$;
REVOKE ALL ON FUNCTION provider_state.real_count_fresh(text) FROM PUBLIC;
CREATE FUNCTION provider_state.real_count_current(cap text) RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
BEGIN PERFORM provider_state.real_source_current(cap);PERFORM provider_state.real_count_fresh(cap);END $$;

REVOKE ALL ON ALL TABLES IN SCHEMA provider_state FROM PUBLIC,whereto_real_worker,whereto_real_issuer,real_token_counter;
REVOKE EXECUTE ON FUNCTION provider_state.app_count_input(text,bytea) FROM real_token_counter;
REVOKE ALL ON FUNCTION provider_state.real_source_current(text),provider_state.real_count_current(text),provider_state.real_enroll_request(text,bytea,bytea,bytea),provider_state.real_count_quote(text,bytea,bytea,uuid),provider_state.real_count_phase(uuid,text),provider_state.real_count_commit(uuid,bigint,bytea),provider_state.real_count_finish(uuid,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION provider_state.real_enroll_request(text,bytea,bytea,bytea) TO whereto_real_issuer;
GRANT EXECUTE ON FUNCTION provider_state.real_count_quote(text,bytea,bytea,uuid),provider_state.real_count_phase(uuid,text),provider_state.real_count_commit(uuid,bigint,bytea),provider_state.real_count_finish(uuid,text) TO real_token_counter;
CREATE FUNCTION provider_state.real_llm_spec(cap text) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE r jsonb;m jsonb;t provider_state.token_counts%ROWTYPE;
BEGIN
 PERFORM provider_state.real_count_current(cap);r:=provider_rules.current_rates();m:=r#>'{models,gpt-6-luna}';SELECT * INTO STRICT t FROM provider_state.token_counts WHERE capability=cap;
 RETURN jsonb_build_object('kind','llm','provider','openai','model',t.model,'model_revision',m->>'revision','account',m->>'account','rate_version',r->>'version','input_tokens',t.input_tokens,'max_output',t.output_cap,'cached_tokens',0,'reasoning_cap',0,'tool_calls',0,
 'prompt_hash',encode(sha256(convert_to((m->'template'->'input'->0)::text,'UTF8')),'hex'),'schema_hash',encode(sha256(convert_to((m->'template'#>'{text,format,schema}')::text,'UTF8')),'hex'),'request_digest',t.request_digest);
END $$;
CREATE FUNCTION provider_state.real_accounting(p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE r jsonb;q jsonb;l jsonb;
BEGIN
 PERFORM provider_state.finance_guard();r:=provider_rules.current_rates();
 IF jsonb_typeof(p) IS DISTINCT FROM 'object' OR (SELECT count(*) FROM jsonb_object_keys(p))<>8 OR NOT(p ?& ARRAY['session','revision','worker','fence','capability','operation','ordinal','payload_digest']) OR NOT provider_rules.integer(p->'ordinal',64) OR (p->>'ordinal')::int<1 THEN RAISE EXCEPTION 'real_accounting_arguments'; END IF;
 PERFORM provider_state.protocol('read',p-ARRAY['capability','operation','ordinal','payload_digest']);
 SELECT quote INTO STRICT q FROM provider_state.app_operations WHERE operation=(p->>'operation')::uuid;
 l:=q->'lines'->((p->>'ordinal')::int-1);
 IF q->>'session' IS DISTINCT FROM p->>'session' OR q->>'capability' IS DISTINCT FROM p->>'capability' OR q->'revision' IS DISTINCT FROM p->'revision' OR q->>'worker' IS DISTINCT FROM p->>'worker' OR q->'fence' IS DISTINCT FROM p->'fence'
 OR l->>'request_digest' IS DISTINCT FROM p->>'payload_digest' OR l IS NULL
 OR q->>'policy' IS DISTINCT FROM encode(sha256(convert_to(r::text,'UTF8')),'hex') OR q->>'epoch' IS DISTINCT FROM (SELECT grant_doc->>'epoch' FROM provider_rules.configuration)
 OR provider_rules.now_at()>=(SELECT (grant_doc->>'expires')::timestamptz FROM provider_rules.configuration)
 OR NOT EXISTS(SELECT 1 FROM provider_state.app_witness_facts WHERE id='deliver:'||(p->>'operation')||':'||(p->>'ordinal')) THEN RAISE EXCEPTION 'real_accounting_delivery'; END IF;
 IF l->>'kind'='llm' THEN PERFORM provider_state.real_count_fresh(p->>'capability'); END IF;
 RETURN jsonb_build_object('rates',r,'quote',q,'line',l,'amount',provider_rules.price(jsonb_build_array(l),r));
END $$;
REVOKE ALL ON FUNCTION provider_state.real_llm_spec(text),provider_state.real_accounting(jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION provider_state.real_llm_spec(text) TO whereto_real_issuer;
GRANT EXECUTE ON FUNCTION provider_state.real_accounting(jsonb) TO whereto_real_worker;
CREATE FUNCTION provider_state.real_approve_google(cap text,wire bytea) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE v jsonb;b jsonb;n int;rows_count int;cols_count int;variant text;area jsonb;point jsonb;
BEGIN
 PERFORM provider_state.finance_guard();
 IF octet_length(wire)>65536 OR NOT(convert_from(wire,'UTF8') IS JSON OBJECT WITH UNIQUE KEYS) THEN RAISE EXCEPTION 'real_google_encoding'; END IF;
 v:=convert_from(wire,'UTF8')::jsonb;b:=v->'body';
 IF (SELECT count(*) FROM jsonb_object_keys(v))<>5 OR NOT(v ?& ARRAY['operation','method','url','mask','body']) OR v->>'method' IS DISTINCT FROM 'POST' OR jsonb_typeof(b) IS DISTINCT FROM 'object' THEN RAISE EXCEPTION 'real_google_shape'; END IF;
 IF v->>'operation'='search' THEN
 IF v->>'url' IS DISTINCT FROM 'https://places.googleapis.com/v1/places:searchText' OR coalesce(v->>'mask','') NOT IN ('places.id,places.displayName,places.formattedAddress,places.location,places.addressComponents,places.attributions,places.types,places.primaryType,nextPageToken','places.id,places.displayName,places.formattedAddress,places.location,places.addressComponents,places.attributions,places.types,places.primaryType,nextPageToken,places.containingPlaces')
 OR EXISTS(SELECT 1 FROM jsonb_object_keys(b) k WHERE k NOT IN ('textQuery','pageSize','languageCode','locationBias','locationRestriction','includedType','strictTypeFiltering'))
 OR jsonb_typeof(b->'textQuery') IS DISTINCT FROM 'string' OR length(b->>'textQuery') NOT BETWEEN 1 AND 1000 OR b->>'languageCode' IS DISTINCT FROM 'en'
 OR NOT provider_rules.integer(b->'pageSize',10) OR (b->>'pageSize')::int<1
 OR (b ? 'locationBias')=(b ? 'locationRestriction') THEN RAISE EXCEPTION 'real_search_profile'; END IF;
 area:=coalesce(b->'locationBias',b->'locationRestriction');
 IF jsonb_typeof(area) IS DISTINCT FROM 'object' OR (SELECT count(*) FROM jsonb_object_keys(area))<>1 THEN RAISE EXCEPTION 'real_search_geography'; END IF;
 IF area ? 'circle' AND b ? 'locationBias' THEN
 IF (SELECT count(*) FROM jsonb_object_keys(area->'circle'))<>2 OR NOT(area->'circle' ?& ARRAY['center','radius']) OR jsonb_typeof(area#>'{circle,radius}') IS DISTINCT FROM 'number' OR (area#>>'{circle,radius}')::numeric NOT BETWEEN 0 AND 50000 THEN RAISE EXCEPTION 'real_search_circle'; END IF;
 ELSIF area ? 'rectangle' THEN
 IF (SELECT count(*) FROM jsonb_object_keys(area->'rectangle'))<>2 OR NOT(area->'rectangle' ?& ARRAY['low','high']) OR (area#>>'{rectangle,low,latitude}')::numeric>(area#>>'{rectangle,high,latitude}')::numeric THEN RAISE EXCEPTION 'real_search_rectangle'; END IF;
 ELSE RAISE EXCEPTION 'real_search_geography'; END IF;
 FOR point IN SELECT area#>'{circle,center}' WHERE area ? 'circle' UNION ALL SELECT area#>'{rectangle,low}' WHERE area ? 'rectangle' UNION ALL SELECT area#>'{rectangle,high}' WHERE area ? 'rectangle' LOOP
 IF jsonb_typeof(point) IS DISTINCT FROM 'object' OR (SELECT count(*) FROM jsonb_object_keys(point))<>2 OR NOT(point ?& ARRAY['latitude','longitude']) OR jsonb_typeof(point->'latitude') IS DISTINCT FROM 'number' OR jsonb_typeof(point->'longitude') IS DISTINCT FROM 'number' OR (point->>'latitude')::numeric NOT BETWEEN -90 AND 90 OR (point->>'longitude')::numeric NOT BETWEEN -180 AND 180 THEN RAISE EXCEPTION 'real_search_coordinates'; END IF; END LOOP;
 IF (b ? 'strictTypeFiltering' AND jsonb_typeof(b->'strictTypeFiltering') IS DISTINCT FROM 'boolean') OR (b ? 'includedType' AND (jsonb_typeof(b->'includedType') IS DISTINCT FROM 'string' OR length(b->>'includedType') NOT BETWEEN 1 AND 100)) THEN RAISE EXCEPTION 'real_search_type'; END IF;
 rows_count:=0;cols_count:=0;variant:='pro';
 ELSIF v->>'operation'='matrix' THEN
 IF v->>'url' IS DISTINCT FROM 'https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix' OR v->>'mask' IS DISTINCT FROM 'originIndex,destinationIndex,status,condition,distanceMeters,duration,fallbackInfo'
 OR jsonb_typeof(b->'origins') IS DISTINCT FROM 'array' OR jsonb_typeof(b->'destinations') IS DISTINCT FROM 'array' THEN RAISE EXCEPTION 'real_matrix_profile'; END IF;
 rows_count:=jsonb_array_length(b->'origins');cols_count:=jsonb_array_length(b->'destinations');
 IF rows_count<1 OR cols_count<1 OR rows_count::bigint*cols_count>300 OR (SELECT count(*) FROM jsonb_array_elements((b->'origins')||(b->'destinations')) p WHERE p#>'{waypoint,placeId}' IS NOT NULL)>50 THEN RAISE EXCEPTION 'real_matrix_units'; END IF;
 IF b->>'travelMode'='DRIVE' THEN
 IF (SELECT count(*) FROM jsonb_object_keys(b))<>4 OR NOT(b ?& ARRAY['origins','destinations','travelMode','routingPreference']) OR b->>'routingPreference' IS DISTINCT FROM 'TRAFFIC_AWARE' THEN RAISE EXCEPTION 'real_drive_profile'; END IF;variant:='drive';
 ELSIF b->>'travelMode'='WALK' THEN
 IF (SELECT count(*) FROM jsonb_object_keys(b))<>3 OR NOT(b ?& ARRAY['origins','destinations','travelMode']) THEN RAISE EXCEPTION 'real_walk_profile'; END IF;variant:='walk';
 ELSE RAISE EXCEPTION 'real_travel_mode'; END IF;
 FOR point IN SELECT value FROM jsonb_array_elements((b->'origins')||(b->'destinations')) LOOP
 IF jsonb_typeof(point) IS DISTINCT FROM 'object' OR (SELECT count(*) FROM jsonb_object_keys(point))<>1 OR NOT(point ? 'waypoint') OR jsonb_typeof(point->'waypoint') IS DISTINCT FROM 'object' OR (SELECT count(*) FROM jsonb_object_keys(point->'waypoint'))<>1 THEN RAISE EXCEPTION 'real_waypoint'; END IF;
 IF point->'waypoint' ? 'placeId' THEN
 IF jsonb_typeof(point#>'{waypoint,placeId}') IS DISTINCT FROM 'string' OR (length(point#>>'{waypoint,placeId}') NOT BETWEEN 1 AND 256 OR (point#>>'{waypoint,placeId}') !~ '^[A-Za-z0-9_-]+$') THEN RAISE EXCEPTION 'real_place_id'; END IF;
 ELSE
 IF NOT(point->'waypoint' ? 'location') OR jsonb_typeof(point#>'{waypoint,location}') IS DISTINCT FROM 'object' OR (SELECT count(*) FROM jsonb_object_keys(point#>'{waypoint,location}'))<>1 OR NOT(point#>'{waypoint,location}' ? 'latLng') THEN RAISE EXCEPTION 'real_waypoint_location'; END IF;
 area:=point#>'{waypoint,location,latLng}';
 IF jsonb_typeof(area) IS DISTINCT FROM 'object' OR (SELECT count(*) FROM jsonb_object_keys(area))<>2 OR NOT(area ?& ARRAY['latitude','longitude']) OR jsonb_typeof(area->'latitude') IS DISTINCT FROM 'number' OR jsonb_typeof(area->'longitude') IS DISTINCT FROM 'number' OR (area->>'latitude')::numeric NOT BETWEEN -90 AND 90 OR (area->>'longitude')::numeric NOT BETWEEN -180 AND 180 THEN RAISE EXCEPTION 'real_waypoint_coordinates'; END IF;
 END IF; END LOOP;
 ELSE RAISE EXCEPTION 'real_google_operation'; END IF;
 PERFORM provider_state.approve_requests(cap,jsonb_build_array(jsonb_build_object('operation',v->>'operation','variant',variant,'rows',rows_count,'cols',cols_count,'request_digest',encode(sha256(wire),'hex'))));
END $$;
REVOKE ALL ON FUNCTION provider_state.approve_requests(text,jsonb) FROM whereto_real_issuer;
REVOKE ALL ON FUNCTION provider_state.real_approve_google(text,bytea) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION provider_state.real_approve_google(text,bytea) TO whereto_real_issuer;
CREATE FUNCTION provider_state.real_counter_observed() RETURNS jsonb LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$ SELECT provider_state.app_observed() $$;
REVOKE ALL ON FUNCTION provider_state.real_counter_observed() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION provider_state.real_counter_observed() TO real_token_counter;
CREATE FUNCTION provider_state.real_register_inference(sid text,http text,inference text) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE s provider_state.sessions%ROWTYPE;e provider_state.evidence%ROWTYPE;
BEGIN
 PERFORM provider_state.finance_guard();SELECT * INTO STRICT s FROM provider_state.sessions WHERE id=sid;SELECT * INTO STRICT e FROM provider_state.evidence WHERE session=sid;
 IF s.kind<>'provider_action' OR s.revision<>1 OR s.revoked OR s.expires<=provider_state.protocol_now() OR e.revision<>s.revision OR e.integrity<>sha256(convert_to(e.payload::text,'UTF8'))
 OR e.payload->>'purpose' IS DISTINCT FROM 'ordinary' OR e.payload->'requestRevision' IS DISTINCT FROM '1'::jsonb OR e.payload->>'interpretationDigest' IS DISTINCT FROM encode(sha256(convert_to('null','UTF8')),'hex')
 OR NOT EXISTS(SELECT 1 FROM provider_state.admission_leases WHERE id=http AND domain='http' AND worker=s.worker AND refs>0)
 OR NOT EXISTS(SELECT 1 FROM provider_state.admission_leases WHERE id=inference AND domain='inference' AND worker=s.worker AND refs>0 AND fingerprint=e.payload->>'sourceDigest') THEN RAISE EXCEPTION 'real_fresh_inference_source'; END IF;
 INSERT INTO provider_state.bridge_actions VALUES(sid,'ordinary',e.payload->>'sourceDigest',e.payload->>'interpretationDigest',1,http,inference,NULL);
END $$;
REVOKE ALL ON FUNCTION provider_state.real_register_inference(text,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION provider_state.real_register_inference(text,text,text) TO whereto_real_issuer;
