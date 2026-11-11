-- V4 additive local protocol. Installed atomically after the V3 pricing layer.
CREATE TABLE synthetic_state.bridge_actions (
 session text PRIMARY KEY REFERENCES synthetic_state.sessions(id),
 purpose text NOT NULL, source_digest text NOT NULL, interpretation_digest text NOT NULL,
 request_revision bigint NOT NULL, http_id text NOT NULL REFERENCES synthetic_state.admission_leases(id),
 inference_id text REFERENCES synthetic_state.admission_leases(id), refresh_key text
);
CREATE TABLE synthetic_state.refresh_claims (
 action text NOT NULL REFERENCES synthetic_state.bridge_actions(session),
 refresh_key text NOT NULL, expires timestamptz NOT NULL, PRIMARY KEY(action)
);
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON synthetic_state.bridge_actions FOR EACH ROW EXECUTE FUNCTION synthetic_state.immutable();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON synthetic_state.refresh_claims FOR EACH ROW EXECUTE FUNCTION synthetic_state.immutable();
CREATE FUNCTION synthetic_state.register_action(sid text, http text, inference text, refresh text) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE s synthetic_state.sessions%ROWTYPE; e synthetic_state.evidence%ROWTYPE; h synthetic_state.admission_leases%ROWTYPE;
BEGIN
 PERFORM synthetic_state.finance_guard();
 SELECT * INTO STRICT s FROM synthetic_state.sessions WHERE id=sid;
 SELECT * INTO STRICT e FROM synthetic_state.evidence WHERE session=sid;
 SELECT * INTO STRICT h FROM synthetic_state.admission_leases WHERE id=http;
 IF s.kind<>'provider_action' OR s.revoked OR s.expires<=synthetic_state.protocol_now() OR e.revision<>s.revision
 OR e.integrity<>sha256(convert_to(e.payload::text,'UTF8')) OR h.domain<>'http' OR h.refs<=0 OR h.worker<>s.worker
 THEN RAISE EXCEPTION 'action_binding'; END IF;
 IF inference IS NOT NULL AND NOT EXISTS(SELECT 1 FROM synthetic_state.admission_leases WHERE id=inference AND domain='inference' AND worker=h.worker AND refs=0 AND fingerprint=e.payload->>'sourceDigest')
 THEN RAISE EXCEPTION 'inference_binding'; END IF;
 IF (e.payload->>'purpose'='refresh')<>(refresh IS NOT NULL) THEN RAISE EXCEPTION 'refresh_purpose'; END IF;
 INSERT INTO synthetic_state.bridge_actions VALUES(sid,e.payload->>'purpose',e.payload->>'sourceDigest',e.payload->>'interpretationDigest',
 (e.payload->>'requestRevision')::bigint,http,inference,refresh);
END $$;
CREATE FUNCTION synthetic_state.bridge_protocol(a text,p jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE b synthetic_state.bridge_actions%ROWTYPE; s synthetic_state.sessions%ROWTYPE; h synthetic_state.admission_leases%ROWTYPE; result jsonb;
BEGIN
 IF a IS NULL OR jsonb_typeof(p) IS DISTINCT FROM 'object' THEN RAISE EXCEPTION 'arguments'; END IF;
 PERFORM synthetic_state.finance_guard();
 IF a IN ('reserve','dispatch') THEN
   SELECT * INTO STRICT b FROM synthetic_state.bridge_actions WHERE session=p->>'session';
   SELECT * INTO STRICT s FROM synthetic_state.sessions WHERE id=b.session;
   SELECT * INTO STRICT h FROM synthetic_state.admission_leases WHERE id=b.http_id;
   IF h.refs<=0 OR h.worker IS DISTINCT FROM (p->>'worker')::uuid OR s.worker<>h.worker
     OR s.revoked OR s.expires<=synthetic_state.protocol_now() THEN RAISE EXCEPTION 'admission_action'; END IF;
   -- Core read validates current revision/fence and private evidence integrity.
   result:=synthetic_state.protocol('read',p-ARRAY['capability','operation','ordinal','payload_digest']);
   IF result->'payload'->>'sourceDigest' IS DISTINCT FROM b.source_digest OR
      result->'payload'->>'interpretationDigest' IS DISTINCT FROM b.interpretation_digest OR
      result->'payload'->>'purpose' IS DISTINCT FROM b.purpose OR
      (result->'payload'->>'requestRevision')::bigint<>b.request_revision THEN RAISE EXCEPTION 'action_changed'; END IF;
   IF b.refresh_key IS NOT NULL AND EXISTS(SELECT 1 FROM synthetic_state.refresh_claims WHERE refresh_key=b.refresh_key AND action<>b.session AND expires>synthetic_state.protocol_now()) THEN RAISE EXCEPTION 'refresh_replay'; END IF;
   IF a='dispatch' THEN
     IF NOT EXISTS(SELECT 1 FROM synthetic_state.financial_lines WHERE operation=(p->>'operation')::uuid AND ordinal=(p->>'ordinal')::int AND request_digest=p->>'payload_digest') THEN RAISE EXCEPTION 'payload_binding'; END IF;
     p:=p-'payload_digest';
   END IF;
   result:=synthetic_state.financial_protocol(a,p);
   IF a='reserve' AND b.refresh_key IS NOT NULL THEN
     INSERT INTO synthetic_state.refresh_claims VALUES(b.session,b.refresh_key,synthetic_state.protocol_now()+interval '1800 seconds') ON CONFLICT DO NOTHING;
   END IF;
   RETURN result;
 END IF;
 RETURN synthetic_state.financial_protocol(a,p);
END $$;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA synthetic_state FROM PUBLIC,whereto_synthetic_worker;
REVOKE ALL ON ALL TABLES IN SCHEMA synthetic_state FROM PUBLIC,whereto_synthetic_worker;
GRANT EXECUTE ON FUNCTION synthetic_state.bridge_protocol(text,jsonb) TO whereto_synthetic_worker;
GRANT EXECUTE ON FUNCTION synthetic_state.register_action(text,text,text,text) TO whereto_synthetic_issuer;
