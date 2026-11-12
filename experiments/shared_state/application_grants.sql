-- New synthetic profile only; frozen evidence/financial/bridge routines unchanged.
ALTER TABLE synthetic_state.operations DROP CONSTRAINT operations_provider_check;
ALTER TABLE synthetic_state.operations ADD CHECK(provider IN ('synthetic_maps','synthetic_ai'));
ALTER TABLE synthetic_state.financial_lines DROP CONSTRAINT financial_lines_provider_check;
ALTER TABLE synthetic_state.financial_lines ADD CHECK(provider IN ('synthetic_maps','synthetic_ai'));
CREATE TABLE synthetic_state.app_permits(id text PRIMARY KEY,phase text NOT NULL,quote jsonb NOT NULL);
CREATE TABLE synthetic_state.app_operations(operation uuid PRIMARY KEY REFERENCES synthetic_state.operations(id),quote jsonb NOT NULL);
CREATE TABLE synthetic_state.app_witness_facts(id text PRIMARY KEY,quote jsonb NOT NULL);
CREATE TABLE synthetic_state.app_sources(inference text PRIMARY KEY,root uuid NOT NULL,outing uuid NOT NULL,source_digest text NOT NULL);
CREATE TABLE synthetic_state.token_counts(capability text PRIMARY KEY REFERENCES synthetic_state.capabilities(id),request_digest text NOT NULL,input_tokens bigint NOT NULL,model text NOT NULL,output_cap bigint NOT NULL);
CREATE TABLE synthetic_state.llm_plans(capability text PRIMARY KEY REFERENCES synthetic_state.capabilities(id),spec jsonb NOT NULL,http text NOT NULL,inference text NOT NULL);
CREATE TABLE synthetic_state.llm_usage(sequence bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,operation uuid NOT NULL REFERENCES synthetic_state.operations(id),report jsonb NOT NULL,valid boolean NOT NULL);
DO $$DECLARE t text;BEGIN
 FOREACH t IN ARRAY ARRAY['app_permits','app_operations','app_witness_facts','llm_plans','llm_usage','app_sources','token_counts'] LOOP
 EXECUTE format('CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON synthetic_state.%I FOR EACH ROW EXECUTE FUNCTION synthetic_state.immutable()',t);END LOOP;
END $$;
CREATE FUNCTION synthetic_state.app_enroll_budget(sid text,root_id uuid,outing_id uuid) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE source_scope synthetic_state.app_sources%ROWTYPE;
BEGIN
 IF NOT EXISTS(SELECT 1 FROM grant_rules.configuration WHERE grant_doc->'roots' @> jsonb_build_array(root_id::text)) THEN RAISE EXCEPTION 'operator_root_required'; END IF;
 SELECT x.* INTO source_scope FROM synthetic_state.app_sources x JOIN synthetic_state.bridge_actions a ON a.inference_id=x.inference WHERE a.session=sid;
 IF FOUND THEN
   IF root_id<>source_scope.root OR (outing_id IS NOT NULL AND outing_id<>source_scope.outing) THEN RAISE EXCEPTION 'source_outing_rebind'; END IF;
   outing_id:=source_scope.outing;
 END IF;
 PERFORM synthetic_state.enroll_budget(sid,root_id,outing_id);
END $$;
CREATE FUNCTION synthetic_state.app_bind_inference(sid text,root_id uuid,outing_id uuid,inference_id text) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE s synthetic_state.sessions%ROWTYPE;e synthetic_state.evidence%ROWTYPE;
BEGIN
 PERFORM synthetic_state.finance_guard();SELECT * INTO STRICT s FROM synthetic_state.sessions WHERE id=sid;SELECT * INTO STRICT e FROM synthetic_state.evidence WHERE session=sid;
 IF NOT EXISTS(SELECT 1 FROM synthetic_state.admission_leases WHERE id=inference_id AND domain='inference' AND refs>0 AND worker=s.worker AND fingerprint=e.payload->>'sourceDigest') THEN RAISE EXCEPTION 'source_inference'; END IF;
 PERFORM synthetic_state.app_enroll_budget(sid,root_id,outing_id);
 INSERT INTO synthetic_state.app_sources VALUES(inference_id,root_id,outing_id,e.payload->>'sourceDigest');
END $$;
CREATE FUNCTION synthetic_state.app_count_input(cap text,wire bytea) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE v jsonb;m jsonb;
BEGIN
 PERFORM synthetic_state.finance_guard();v:=convert_from(wire,'UTF8')::jsonb;
 SELECT rates->'models'->(v->>'model') INTO m FROM grant_rules.configuration WHERE id=1;
 IF jsonb_typeof(v) IS DISTINCT FROM 'object' OR (SELECT count(*) FROM jsonb_object_keys(v))<>10
 OR NOT(v ?& ARRAY['provider','model','system','input','schema','max_output_tokens','reasoning','tools','cache','store'])
 OR m IS NULL OR m->>'profile'<>'fake-utf8-complete-v1' OR v->>'provider' IS DISTINCT FROM m->>'provider'
 OR sha256(convert_to(v->>'system','UTF8'))::text IS DISTINCT FROM ('\x'||(m->>'prompt_hash'))
 OR v->'schema' IS DISTINCT FROM m->'schema' OR NOT grant_rules.integer(v->'max_output_tokens',(m->>'max_output')::numeric)
 OR octet_length(wire)>(m->>'max_input')::int OR v->'reasoning' IS DISTINCT FROM '"none"'::jsonb
 OR v->'tools' IS DISTINCT FROM '[]'::jsonb OR v->'cache' IS DISTINCT FROM 'false'::jsonb OR v->'store' IS DISTINCT FROM 'false'::jsonb
 THEN RAISE EXCEPTION 'complete_input_count'; END IF;
 INSERT INTO synthetic_state.token_counts VALUES(cap,encode(sha256(wire),'hex'),octet_length(wire),v->>'model',(v->>'max_output_tokens')::bigint);
END $$;
CREATE FUNCTION synthetic_state.app_approve_llm(cap text,spec jsonb,http text,inference text) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE c synthetic_state.capabilities%ROWTYPE;s synthetic_state.sessions%ROWTYPE;e synthetic_state.evidence%ROWTYPE;r jsonb;
BEGIN
 PERFORM synthetic_state.finance_guard();
 IF (SELECT profile FROM synthetic_state.finance_policy)<>'bounded' THEN RAISE EXCEPTION 'unreviewed_inference_budget_profile'; END IF;
 SELECT * INTO STRICT c FROM synthetic_state.capabilities WHERE id=cap;
 SELECT * INTO STRICT s FROM synthetic_state.sessions WHERE id=c.session;SELECT * INTO STRICT e FROM synthetic_state.evidence WHERE session=s.id;
 SELECT rates INTO STRICT r FROM grant_rules.configuration WHERE id=1;
 PERFORM grant_rules.price(jsonb_build_array(spec),r);
 IF NOT EXISTS(SELECT 1 FROM synthetic_state.token_counts WHERE capability=cap AND request_digest=spec->>'request_digest' AND input_tokens=(spec->>'input_tokens')::bigint AND model=spec->>'model' AND output_cap=(spec->>'max_output')::bigint) THEN RAISE EXCEPTION 'count_attestation'; END IF;
 IF c.purpose<>'provider_action' OR s.revoked OR s.revision<>c.revision OR s.expires<=synthetic_state.protocol_now()
 OR NOT EXISTS(SELECT 1 FROM synthetic_state.admission_leases WHERE id=http AND domain='http' AND refs>0 AND worker=s.worker)
 OR NOT EXISTS(SELECT 1 FROM synthetic_state.admission_leases WHERE id=inference AND domain='inference' AND refs>0 AND worker=s.worker AND fingerprint=e.payload->>'sourceDigest')
 THEN RAISE EXCEPTION 'inference_owner'; END IF;
 INSERT INTO synthetic_state.llm_plans VALUES(cap,spec,http,inference);
END $$;
CREATE FUNCTION synthetic_state.app_quote(p jsonb) RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
DECLARE g jsonb;r jsonb;b record;llm synthetic_state.llm_plans%ROWTYPE;lines jsonb;provider_name text;charge bigint;
BEGIN
 PERFORM synthetic_state.finance_guard();
 PERFORM synthetic_state.protocol('read',p-ARRAY['capability','operation','ordinal','payload_digest']);
 SELECT grant_doc,rates INTO STRICT g,r FROM grant_rules.configuration WHERE id=1;
 IF NOT EXISTS(SELECT 1 FROM synthetic_state.capabilities WHERE id=p->>'capability' AND session=p->>'session' AND revision=(p->>'revision')::bigint) THEN RAISE EXCEPTION 'quote_capability'; END IF;
 SELECT o.id AS outing,o.root INTO STRICT b FROM synthetic_state.budget_bindings bb JOIN synthetic_state.budget_outings o ON o.id=bb.outing WHERE bb.session=p->>'session';
 SELECT * INTO llm FROM synthetic_state.llm_plans WHERE capability=p->>'capability';
 IF FOUND THEN lines:=jsonb_build_array(llm.spec);provider_name:=llm.spec->>'provider';
 ELSE
   SELECT jsonb_agg(jsonb_build_object('kind','maps','sku',sku,'units',units,'rate_version',rate_version,'request_digest',request_digest) ORDER BY ordinal)
    INTO lines FROM synthetic_state.request_plans WHERE capability=p->>'capability';provider_name:='synthetic_maps';
 END IF;
 charge:=grant_rules.price(lines,r);
 RETURN jsonb_build_object('operation',p->>'operation','session',p->>'session','capability',p->>'capability','revision',p->'revision','fence',p->'fence','worker',p->>'worker',
 'grant',g->>'id','version',g->>'version','epoch',g->>'epoch','provider',provider_name,'root',b.root,'outing',b.outing,
 'day',(grant_rules.now_at() AT TIME ZONE (g->>'timezone'))::date,'charge',charge,'lines',lines);
END $$;
CREATE FUNCTION synthetic_state.app_observed() RETURNS jsonb LANGUAGE sql SET search_path=pg_catalog,pg_temp AS $$
 SELECT coalesce(jsonb_object_agg(id,sha256(convert_to(quote::text,'UTF8'))::text),'{}'::jsonb) FROM synthetic_state.app_witness_facts
$$;
CREATE FUNCTION synthetic_state.app_accept(id text,phase text,q jsonb) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE stored jsonb;g jsonb;
BEGIN
 PERFORM synthetic_state.finance_guard();SELECT grant_doc INTO STRICT g FROM grant_rules.configuration WHERE configuration.id=1;
 IF q->>'epoch' IS DISTINCT FROM g->>'epoch' OR phase NOT IN ('reserve','dispatch','deliver')
 OR id IS DISTINCT FROM (phase||':'||(q->>'operation')||(CASE WHEN phase='reserve' THEN '' ELSE ':'||split_part(id,':',3) END)) THEN RAISE EXCEPTION 'witness_permit'; END IF;
 IF phase='reserve' THEN
   stored:=synthetic_state.app_quote(jsonb_build_object('session',q->'session','revision',q->'revision','worker',q->'worker','fence',q->'fence','capability',q->'capability','operation',q->'operation'));
 ELSE SELECT quote INTO STRICT stored FROM synthetic_state.app_operations WHERE operation=(q->>'operation')::uuid;END IF;
 IF stored IS DISTINCT FROM q THEN RAISE EXCEPTION 'quote_changed'; END IF;
 INSERT INTO synthetic_state.app_permits VALUES(id,phase,q);
END $$;
CREATE FUNCTION synthetic_state.app_protocol(a text,p jsonb,env text,ep text,proof text) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE g jsonb;q jsonb;permit synthetic_state.app_permits%ROWTYPE;llm synthetic_state.llm_plans%ROWTYPE;att synthetic_state.evidence_attestations%ROWTYPE;
 result jsonb;used record;active bigint;identifier text;now_at timestamptz;budget record;valid_usage boolean;allowed_fields text[];
BEGIN
 PERFORM synthetic_state.finance_guard();SELECT grant_doc INTO STRICT g FROM grant_rules.configuration WHERE id=1;
 IF env IS DISTINCT FROM 'synthetic' OR ep IS DISTINCT FROM g->>'epoch' THEN RAISE EXCEPTION 'grant_epoch'; END IF;
 IF a='transition' AND p->>'state'='SUCCEEDED' THEN
   IF NOT EXISTS(SELECT 1 FROM synthetic_state.app_operations WHERE operation=(p->>'operation')::uuid)
    OR (SELECT count(*) FROM synthetic_state.app_witness_facts WHERE id LIKE 'deliver:'||(p->>'operation')||':%')<>jsonb_array_length((SELECT quote->'lines' FROM synthetic_state.app_operations WHERE operation=(p->>'operation')::uuid))
    OR (EXISTS(SELECT 1 FROM synthetic_state.llm_plans l JOIN synthetic_state.operations o ON o.capability=l.capability WHERE o.id=(p->>'operation')::uuid) AND (NOT EXISTS(SELECT 1 FROM synthetic_state.llm_usage WHERE operation=(p->>'operation')::uuid AND valid) OR EXISTS(SELECT 1 FROM synthetic_state.llm_usage WHERE operation=(p->>'operation')::uuid AND NOT valid))) THEN RAISE EXCEPTION 'complete_delivery_and_usage_required'; END IF;
 END IF;
 IF a='app_reserved' THEN RETURN (SELECT quote FROM synthetic_state.app_operations WHERE operation=(p->>'operation')::uuid); END IF;
 IF a='app_observed' AND p='{}' THEN RETURN synthetic_state.app_observed(); END IF;
 IF a='app_quote' THEN RETURN synthetic_state.app_quote(p); END IF;
 IF a='app_state' THEN RETURN jsonb_build_object('state',(SELECT kind FROM synthetic_state.facts WHERE operation=(p->>'operation')::uuid ORDER BY sequence DESC LIMIT 1)); END IF;
 IF a IN ('reserve','dispatch','app_deliver') THEN
   IF grant_rules.now_at()>=(g->>'expires')::timestamptz THEN RAISE EXCEPTION 'expired_grant'; END IF;
   allowed_fields:=CASE a WHEN 'reserve' THEN ARRAY['session','revision','worker','fence','capability','operation'] ELSE ARRAY['session','revision','worker','fence','capability','operation','ordinal','payload_digest'] END;
   IF jsonb_typeof(p) IS DISTINCT FROM 'object' OR (SELECT count(*) FROM jsonb_object_keys(p))<>cardinality(allowed_fields) OR NOT(p ?& allowed_fields) THEN RAISE EXCEPTION 'app_arguments'; END IF;
   q:=CASE WHEN a='reserve' THEN synthetic_state.app_quote(p) ELSE (SELECT quote FROM synthetic_state.app_operations WHERE operation=(p->>'operation')::uuid) END;
   identifier:=CASE a WHEN 'reserve' THEN 'reserve:' WHEN 'dispatch' THEN 'dispatch:' ELSE 'deliver:' END||(p->>'operation')||CASE WHEN a='reserve' THEN '' ELSE ':'||(p->>'ordinal') END;
   SELECT * INTO STRICT permit FROM synthetic_state.app_permits WHERE id=identifier;
   IF permit.quote IS DISTINCT FROM q THEN RAISE EXCEPTION 'permit_binding'; END IF;
   IF a='app_deliver' THEN
     PERFORM synthetic_state.protocol('read',p-ARRAY['capability','operation','ordinal','payload_digest']);
     IF NOT EXISTS(SELECT 1 FROM synthetic_state.financial_dispatch WHERE operation=(p->>'operation')::uuid AND ordinal=(p->>'ordinal')::int)
      OR q->'lines'->((p->>'ordinal')::int-1)->>'request_digest' IS DISTINCT FROM p->>'payload_digest' THEN RAISE EXCEPTION 'transport_intent'; END IF;
     INSERT INTO synthetic_state.app_witness_facts VALUES(identifier,q);RETURN '{}'::jsonb;
   END IF;
   SELECT * INTO llm FROM synthetic_state.llm_plans WHERE capability=p->>'capability';
   IF a='reserve' THEN
     SELECT coalesce(sum((quote->>'charge')::numeric),0) t,coalesce(sum((quote->>'charge')::numeric) FILTER(WHERE quote->>'provider'=q->>'provider'),0) pr,
       coalesce(sum((quote->>'charge')::numeric) FILTER(WHERE quote->>'day'=q->>'day'),0) d,coalesce(sum((quote->>'charge')::numeric) FILTER(WHERE quote->>'outing'=q->>'outing'),0) o,count(*) n INTO used FROM synthetic_state.app_operations;
     SELECT count(*) INTO active FROM synthetic_state.app_operations x WHERE coalesce((SELECT kind FROM synthetic_state.facts WHERE operation=x.operation ORDER BY sequence DESC LIMIT 1),'MISSING') NOT IN ('SUCCEEDED','FAILED');
     PERFORM grant_rules.check_limit(q,used.t,used.pr,used.d,used.o,used.n,active);
   END IF;
   IF llm.capability IS NULL THEN
     result:=synthetic_state.evidence_protocol(a,p,env,ep,proof);
   ELSE
     -- Frozen evidence front door has no inference variant: reuse its immutable
     -- attestation tables and core fence reader, adding only the typed LLM branch.
     PERFORM synthetic_state.evidence_protocol('read',p-ARRAY['capability','operation','ordinal','payload_digest'],env,ep,NULL);
     SELECT * INTO STRICT att FROM synthetic_state.evidence_attestations WHERE nonce=proof;
     IF att.command<>a OR att.request<>p OR att.epoch<>ep OR att.expires<=clock_timestamp()
      OR att.commitment IS DISTINCT FROM (SELECT commitment FROM synthetic_state.evidence_anchors WHERE session=p->>'session') THEN RAISE EXCEPTION 'llm_evidence'; END IF;
     INSERT INTO synthetic_state.evidence_attestation_uses VALUES(proof);
     IF NOT EXISTS(SELECT 1 FROM synthetic_state.admission_leases WHERE id=llm.http AND domain='http' AND refs>0 AND worker=(p->>'worker')::uuid)
      OR NOT EXISTS(SELECT 1 FROM synthetic_state.admission_leases WHERE id=llm.inference AND domain='inference' AND refs>0 AND worker=(p->>'worker')::uuid) THEN RAISE EXCEPTION 'llm_admission'; END IF;
     now_at:=synthetic_state.protocol_now();
     IF a='reserve' THEN
       SELECT count(*) req INTO used FROM synthetic_state.financial_lines WHERE root=(q->>'root')::uuid;
       IF used.req+1>(SELECT (settings->>'requests_per_session')::int FROM synthetic_state.finance_policy)
        OR (SELECT count(*)+1 FROM synthetic_state.financial_lines WHERE outing=(q->>'outing')::uuid)>(SELECT (settings->>'requests_per_outing')::int FROM synthetic_state.finance_policy)
        OR EXISTS(SELECT 1 FROM synthetic_state.financial_lines f WHERE f.root=(q->>'root')::uuid AND (SELECT kind FROM synthetic_state.facts WHERE operation=f.operation ORDER BY sequence DESC LIMIT 1) NOT IN ('SUCCEEDED','FAILED')) THEN RAISE EXCEPTION 'llm_root_budget'; END IF;
       PERFORM synthetic_state.protocol('reserve',p||jsonb_build_object('provider','synthetic_ai','charge',(q->>'charge')::bigint));
       INSERT INTO synthetic_state.financial_lines VALUES((p->>'operation')::uuid,1,(q->>'root')::uuid,(q->>'outing')::uuid,'inference',llm.spec->>'request_digest',llm.spec->>'rate_version',1,(q->>'charge')::bigint,llm.spec->>'rate_version',(q->>'charge')::bigint,'synthetic_ai','synthetic-application-grant-v1','synthetic-local-project-v1','USD',now_at,(now_at AT TIME ZONE (SELECT timezone FROM synthetic_state.finance_policy))::date,(SELECT timezone FROM synthetic_state.finance_policy));
     ELSE
       IF p->'ordinal' IS DISTINCT FROM '1'::jsonb OR p->>'payload_digest' IS DISTINCT FROM llm.spec->>'request_digest'
        OR NOT EXISTS(SELECT 1 FROM synthetic_state.operations WHERE id=(p->>'operation')::uuid AND capability=p->>'capability' AND session=p->>'session' AND worker=(p->>'worker')::uuid AND fence=(p->>'fence')::bigint)
        OR (SELECT kind FROM synthetic_state.facts WHERE operation=(p->>'operation')::uuid ORDER BY sequence DESC LIMIT 1)<>'INTENT' THEN RAISE EXCEPTION 'llm_dispatch'; END IF;
       INSERT INTO synthetic_state.financial_dispatch VALUES((p->>'operation')::uuid,1,now_at);
     END IF;
     result:='{}'::jsonb;
   END IF;
   IF a='reserve' AND (SELECT charge FROM synthetic_state.operations WHERE id=(p->>'operation')::uuid) IS DISTINCT FROM (q->>'charge')::bigint THEN RAISE EXCEPTION 'reserved_price_mismatch'; END IF;
   IF a='reserve' THEN INSERT INTO synthetic_state.app_operations VALUES((p->>'operation')::uuid,q); END IF;
   INSERT INTO synthetic_state.app_witness_facts VALUES(identifier,q);
   RETURN result;
 ELSIF a='app_usage' THEN
   SELECT * INTO STRICT llm FROM synthetic_state.llm_plans WHERE capability=p->>'capability';
   PERFORM synthetic_state.protocol('read',p-ARRAY['capability','operation','report']);
   IF NOT EXISTS(SELECT 1 FROM synthetic_state.operations WHERE id=(p->>'operation')::uuid AND capability=llm.capability AND session=p->>'session') THEN RAISE EXCEPTION 'usage_owner'; END IF;
   valid_usage:=false;
   IF jsonb_typeof(p->'report')='object' THEN valid_usage:= (SELECT count(*) FROM jsonb_object_keys(p->'report'))=7
     AND p->'report'->>'provider'=llm.spec->>'provider' AND p->'report'->>'model'=llm.spec->>'model'
     AND p->'report'->'input_tokens'=llm.spec->'input_tokens' AND grant_rules.integer(p->'report'->'output_tokens',(llm.spec->>'max_output')::numeric)
     AND p->'report'->'cached_tokens'='0'::jsonb AND p->'report'->'reasoning_tokens'='0'::jsonb AND p->'report'->'tool_calls'='0'::jsonb
     AND NOT EXISTS(SELECT 1 FROM synthetic_state.llm_usage WHERE operation=(p->>'operation')::uuid AND report<>p->'report'); END IF;
   INSERT INTO synthetic_state.llm_usage(operation,report,valid) VALUES((p->>'operation')::uuid,coalesce(p->'report','null'::jsonb),coalesce(valid_usage,false));
   RETURN jsonb_build_object('valid',coalesce(valid_usage,false),'refund',false,'released',0,'reportedCharge',CASE WHEN valid_usage THEN grant_rules.price(jsonb_build_array(jsonb_set(llm.spec,'{max_output}',p->'report'->'output_tokens')),(SELECT rates FROM grant_rules.configuration WHERE id=1)) ELSE NULL END);
 END IF;
 result:=synthetic_state.evidence_protocol(a,p,env,ep,proof);
 IF a='transition' AND p->>'state' IN ('SUCCEEDED','FAILED','UNCERTAIN') THEN
   SELECT quote INTO STRICT q FROM synthetic_state.app_operations WHERE operation=(p->>'operation')::uuid;
   INSERT INTO synthetic_state.app_witness_facts VALUES('outcome:'||(p->>'operation'),q||jsonb_build_object('state',p->>'state'));
 END IF;
 RETURN result;
END $$;
REVOKE ALL ON ALL TABLES IN SCHEMA synthetic_state,grant_rules FROM PUBLIC,whereto_synthetic_worker,whereto_synthetic_issuer;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA synthetic_state FROM PUBLIC,whereto_synthetic_worker;
REVOKE EXECUTE ON FUNCTION synthetic_state.enroll_budget(text,uuid,uuid) FROM whereto_synthetic_issuer;
GRANT EXECUTE ON FUNCTION synthetic_state.app_protocol(text,jsonb,text,text,text) TO whereto_synthetic_worker;
GRANT EXECUTE ON FUNCTION synthetic_state.app_accept(text,text,jsonb),synthetic_state.app_enroll_budget(text,uuid,uuid),synthetic_state.app_approve_llm(text,jsonb,text,text) TO whereto_synthetic_issuer;

GRANT EXECUTE ON FUNCTION synthetic_state.app_bind_inference(text,uuid,uuid,text) TO whereto_synthetic_issuer;

GRANT USAGE ON SCHEMA synthetic_state TO synthetic_token_counter;
GRANT EXECUTE ON FUNCTION synthetic_state.app_count_input(text,bytea) TO synthetic_token_counter;
