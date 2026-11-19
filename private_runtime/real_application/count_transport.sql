-- Additive count-transport consumption only; existing financial algorithms unchanged.
CREATE TABLE provider_state.count_transport_uses(operation uuid PRIMARY KEY REFERENCES provider_state.count_attempts(operation),digest text NOT NULL);
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON provider_state.count_transport_uses FOR EACH ROW EXECUTE FUNCTION provider_rules.immutable();
REVOKE ALL ON provider_state.count_transport_uses FROM PUBLIC;
CREATE FUNCTION provider_state.count_transport(op uuid,wire bytea,consume boolean) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE a provider_state.count_attempts%ROWTYPE;r jsonb;
BEGIN
 SELECT * INTO STRICT a FROM provider_state.count_attempts WHERE operation=op;
 r:=provider_state.real_source_current(a.capability);
 IF octet_length(wire)>100000 OR encode(sha256(wire),'hex') IS DISTINCT FROM a.quote#>>'{lines,0,request_digest}'
 OR a.quote->>'policy' IS DISTINCT FROM encode(sha256(convert_to(r::text,'UTF8')),'hex')
 OR a.quote->>'epoch' IS DISTINCT FROM (SELECT grant_doc->>'epoch' FROM provider_rules.configuration WHERE id=1)
 OR NOT EXISTS(SELECT 1 FROM provider_state.app_witness_facts WHERE id='deliver:'||op::text||':1' AND quote=a.quote)
 OR EXISTS(SELECT 1 FROM provider_state.count_outcomes WHERE operation=op)
 OR EXISTS(SELECT 1 FROM provider_state.count_transport_uses WHERE operation=op)
 THEN RAISE EXCEPTION 'count_transport_scope'; END IF;
 IF consume THEN INSERT INTO provider_state.count_transport_uses VALUES(op,encode(sha256(wire),'hex')); END IF;
 RETURN a.quote;
END $$;
REVOKE ALL ON FUNCTION provider_state.count_transport(uuid,bytea,boolean) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION provider_state.count_transport(uuid,bytea,boolean),provider_state.real_counter_observed() TO real_dispatch_client;
