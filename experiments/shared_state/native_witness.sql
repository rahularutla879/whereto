ALTER TABLE witness.claims DROP CONSTRAINT claims_phase_check;
ALTER TABLE witness.claims ADD CHECK(phase IN ('reserve','dispatch','deliver','outcome','checkpoint'));
CREATE FUNCTION witness.native_protocol(a text,p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE g jsonb;q jsonb;ep text;
BEGIN
 IF a<>'checkpoint' THEN RETURN witness.protocol(a,p); END IF;
 PERFORM witness.protocol('confirm',jsonb_build_object('observed',p->'observed'));
 SELECT grant_doc INTO STRICT g FROM grant_rules.configuration WHERE id=1 FOR UPDATE;
 SELECT epoch INTO STRICT ep FROM witness.epochs ORDER BY sequence DESC LIMIT 1;q:=p->'quote';
 IF EXISTS(SELECT 1 FROM witness.events) OR ep IS DISTINCT FROM g->>'epoch' OR q->>'epoch' IS DISTINCT FROM ep OR q->>'grant' IS DISTINCT FROM g->>'id'
 OR q->>'version'<>'52-native-session-reconstruction-local-v1' OR NOT(g->'roots' @> jsonb_build_array(q->>'root')) OR grant_rules.now_at()>=(g->>'expires')::timestamptz THEN RETURN jsonb_build_object('denied','native_witness'); END IF;
 INSERT INTO witness.claims VALUES('native:'||(q->>'session')||':'||(q->>'revision'),'checkpoint',q,0,q->>'provider',(q->>'day')::date,(q->>'outing')::uuid);
 RETURN '{}'::jsonb;
END $$;
REVOKE ALL ON FUNCTION witness.native_protocol(text,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION witness.native_protocol(text,jsonb) TO synthetic_witness_service;
