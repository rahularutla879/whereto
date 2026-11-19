"""Additive application routines over the existing real financial authority."""
from pathlib import Path
from private_runtime.real_finance.profile import verify,replace

def application_sql():
    verify()
    text=(Path(__file__).resolve().parents[1]/'real_finance/counter.sql').read_text()
    start=text.index('CREATE FUNCTION provider_state.real_approve_google(')
    end=text.index('\nREVOKE ALL ON FUNCTION provider_state.approve_requests',start)
    validator=text[start:end]
    validator=replace(validator,'real_approve_google(cap text,wire bytea) RETURNS void','real_google_plan(wire bytea) RETURNS jsonb')
    old="PERFORM provider_state.approve_requests(cap,jsonb_build_array(jsonb_build_object('operation',v->>'operation','variant',variant,'rows',rows_count,'cols',cols_count,'request_digest',encode(sha256(wire),'hex'))));"
    validator=replace(validator,old,"RETURN jsonb_build_object('operation',v->>'operation','variant',variant,'rows',rows_count,'cols',cols_count,'request_digest',encode(sha256(wire),'hex')); ")
    return validator+'''
REVOKE ALL ON FUNCTION provider_state.real_google_plan(bytea) FROM PUBLIC;
CREATE FUNCTION provider_state.real_approve_google_batch(cap text,wires bytea[]) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE wire bytea;plans jsonb:='[]';
BEGIN
 IF wires IS NULL OR cardinality(wires) NOT BETWEEN 1 AND 64 OR array_ndims(wires)<>1 THEN RAISE EXCEPTION 'real_google_batch'; END IF;
 FOREACH wire IN ARRAY wires LOOP
 IF wire IS NULL THEN RAISE EXCEPTION 'real_google_batch'; END IF;
 plans:=plans||jsonb_build_array(provider_state.real_google_plan(wire));END LOOP;
 PERFORM provider_state.approve_requests(cap,plans);
END $$;
REVOKE ALL ON FUNCTION provider_state.real_approve_google_batch(text,bytea[]) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION provider_state.real_approve_google_batch(text,bytea[]) TO whereto_real_issuer;
CREATE FUNCTION provider_state.real_application_input_policy(cap text) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE r jsonb;
BEGIN
 r:=provider_state.real_source_current(cap);
 -- This exact frozen candidate cannot report a cache-write bucket. Never
 -- fabricate zero actual usage for a separately priced, unreported category.
 IF r#>'{models,gpt-6-luna,cache_write_ppm}' IS DISTINCT FROM '0'::jsonb THEN RAISE EXCEPTION 'real_unreported_cache_write_category'; END IF;
END $$;
REVOKE ALL ON FUNCTION provider_state.real_application_input_policy(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION provider_state.real_application_input_policy(text) TO whereto_real_issuer;
CREATE TABLE provider_state.real_response_receipts(operation uuid PRIMARY KEY REFERENCES provider_state.operations(id),request_digest text NOT NULL,response_digest text NOT NULL,usage_digest text NOT NULL);
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON provider_state.real_response_receipts FOR EACH ROW EXECUTE FUNCTION provider_state.immutable();
REVOKE ALL ON provider_state.real_response_receipts FROM PUBLIC,whereto_real_worker,whereto_real_issuer,real_token_counter;
CREATE FUNCTION provider_state.real_capture_response(op uuid,cap text,wire bytea,raw bytea,usage jsonb) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE q jsonb;v jsonb;
BEGIN
 PERFORM provider_state.finance_guard();
 SELECT quote INTO STRICT q FROM provider_state.app_operations WHERE operation=op;
 IF q->>'capability' IS DISTINCT FROM cap OR q->>'provider' IS DISTINCT FROM 'openai' OR jsonb_array_length(q->'lines')<>1
 OR q#>>'{lines,0,request_digest}' IS DISTINCT FROM encode(sha256(wire),'hex') OR octet_length(raw)>700000
 OR NOT EXISTS(SELECT 1 FROM provider_state.app_witness_facts WHERE id='deliver:'||op::text||':1') THEN RAISE EXCEPTION 'real_response_owner'; END IF;
 IF usage IS DISTINCT FROM 'null'::jsonb THEN
 IF NOT(convert_from(raw,'UTF8') IS JSON OBJECT WITH UNIQUE KEYS) THEN RAISE EXCEPTION 'real_response_report'; END IF;
 v:=convert_from(raw,'UTF8')::jsonb;
 IF usage->>'model' IS DISTINCT FROM v->>'model' OR usage->'input_tokens' IS DISTINCT FROM v#>'{usage,input_tokens}' OR usage->'output_tokens' IS DISTINCT FROM v#>'{usage,output_tokens}'
 OR usage->'cache_write_tokens' IS DISTINCT FROM '0'::jsonb OR usage->'tool_calls' IS DISTINCT FROM '0'::jsonb
 OR usage->'cached_tokens' IS DISTINCT FROM coalesce(v#>'{usage,input_tokens_details,cached_tokens}','0'::jsonb)
 OR usage->'reasoning_tokens' IS DISTINCT FROM coalesce(v#>'{usage,output_tokens_details,reasoning_tokens}','0'::jsonb) THEN RAISE EXCEPTION 'real_response_report'; END IF;END IF;
 INSERT INTO provider_state.real_response_receipts VALUES(op,encode(sha256(wire),'hex'),encode(sha256(raw),'hex'),encode(sha256(convert_to(usage::text,'UTF8')),'hex'));
END $$;
REVOKE ALL ON FUNCTION provider_state.real_capture_response(uuid,text,bytea,bytea,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION provider_state.real_capture_response(uuid,text,bytea,bytea,jsonb) TO whereto_real_issuer;
CREATE FUNCTION provider_state.real_application_protocol(a text,p jsonb,env text,ep text,proof text) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 IF a='app_deliver' THEN
 IF NOT EXISTS(SELECT 1 FROM provider_state.bridge_actions b JOIN provider_state.admission_leases h ON h.id=b.http_id WHERE b.session=p->>'session' AND h.domain='http' AND h.refs>0 AND h.worker=(p->>'worker')::uuid) THEN RAISE EXCEPTION 'real_delivery_admission'; END IF;
 IF EXISTS(SELECT 1 FROM provider_state.llm_plans WHERE capability=p->>'capability') AND NOT EXISTS(SELECT 1 FROM provider_state.llm_plans l JOIN provider_state.admission_leases i ON i.id=l.inference WHERE l.capability=p->>'capability' AND i.domain='inference' AND i.refs>0 AND i.worker=(p->>'worker')::uuid) THEN RAISE EXCEPTION 'real_delivery_inference'; END IF;
 END IF;
 IF a='transition' AND p->>'state'='SUCCEEDED' AND EXISTS(SELECT 1 FROM provider_state.operations o JOIN provider_state.llm_plans l ON o.capability=l.capability WHERE o.id=(p->>'operation')::uuid) THEN
 IF NOT EXISTS(SELECT 1 FROM provider_state.real_response_receipts r JOIN provider_state.llm_usage u ON u.operation=r.operation WHERE r.operation=(p->>'operation')::uuid AND u.valid AND r.usage_digest=encode(sha256(convert_to(u.report::text,'UTF8')),'hex')) THEN RAISE EXCEPTION 'real_response_receipt_required'; END IF;
 END IF;
 RETURN provider_state.app_protocol(a,p,env,ep,proof);
END $$;
REVOKE EXECUTE ON FUNCTION provider_state.app_protocol(text,jsonb,text,text,text) FROM whereto_real_worker;
REVOKE ALL ON FUNCTION provider_state.real_application_protocol(text,jsonb,text,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION provider_state.real_application_protocol(text,jsonb,text,text,text) TO whereto_real_worker;
'''
