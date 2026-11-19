CREATE TABLE provider_witness.count_transport_uses(operation uuid PRIMARY KEY,digest text NOT NULL);
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON provider_witness.count_transport_uses FOR EACH ROW EXECUTE FUNCTION provider_rules.immutable();
REVOKE ALL ON provider_witness.count_transport_uses FROM PUBLIC;
CREATE FUNCTION provider_witness.count_transport(q jsonb) RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE r jsonb;
BEGIN
 r:=provider_rules.current_rates();
 IF session_user<>'real_dispatch_witness' OR q->>'epoch' IS DISTINCT FROM provider_witness.epoch()
 OR q->>'policy' IS DISTINCT FROM encode(sha256(convert_to(r::text,'UTF8')),'hex')
 OR q->'charge' IS DISTINCT FROM '0'::jsonb OR jsonb_array_length(q->'lines')<>1 OR q#>>'{lines,0,kind}' IS DISTINCT FROM 'count'
 OR NOT EXISTS(SELECT 1 FROM provider_witness.claims WHERE id='deliver:'||(q->>'operation')||':1' AND quote=q)
 OR EXISTS(SELECT 1 FROM provider_witness.claims WHERE id='outcome:'||(q->>'operation')) THEN RAISE EXCEPTION 'count_transport_witness'; END IF;
 INSERT INTO provider_witness.count_transport_uses VALUES((q->>'operation')::uuid,q#>>'{lines,0,request_digest}');
END $$;
REVOKE ALL ON FUNCTION provider_witness.count_transport(jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION provider_witness.count_transport(jsonb) TO real_dispatch_witness;
