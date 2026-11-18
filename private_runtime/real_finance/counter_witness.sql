-- Separate counter witness principal: may witness ONLY zero-fee count operations.
CREATE FUNCTION provider_witness.counter_protocol(a text,p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE q jsonb;
BEGIN
 IF a IN ('epoch','status','confirm','quarantine') THEN RETURN provider_witness.protocol(a,p); END IF;
 IF a IN ('reserve','dispatch','deliver') THEN q:=p->'quote';
 ELSIF a='outcome' THEN SELECT quote INTO STRICT q FROM provider_witness.claims WHERE id='reserve:'||(p->>'operation');
 ELSE RAISE EXCEPTION 'real_counter_witness_method'; END IF;
 IF q->>'provider' IS DISTINCT FROM 'openai' OR q->'charge' IS DISTINCT FROM '0'::jsonb
 OR jsonb_array_length(q->'lines')<>1 OR q#>>'{lines,0,kind}' IS DISTINCT FROM 'count' THEN RAISE EXCEPTION 'real_counter_witness_scope'; END IF;
 RETURN provider_witness.protocol(a,p);
END $$;
REVOKE ALL ON FUNCTION provider_witness.counter_protocol(text,jsonb) FROM PUBLIC;
GRANT USAGE ON SCHEMA provider_witness TO real_counter_witness;
GRANT EXECUTE ON FUNCTION provider_witness.counter_protocol(text,jsonb),provider_witness.epoch() TO real_counter_witness;
