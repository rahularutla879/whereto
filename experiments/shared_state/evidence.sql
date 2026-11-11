-- Additive disposable-only evidence boundary. No modification of frozen V4 routines.
-- This profile stores only ProviderAction digests here, so metadata must survive SQL crash.
ALTER TABLE synthetic_state.evidence SET LOGGED;
CREATE TABLE synthetic_state.evidence_policy (
 id integer PRIMARY KEY CHECK(id=1), environment text NOT NULL, epoch text NOT NULL,
 version text NOT NULL, CHECK(environment='synthetic'), CHECK(epoch ~ '^[0-9a-f]{64}$')
);
CREATE TABLE synthetic_state.evidence_anchors (
 session text PRIMARY KEY REFERENCES synthetic_state.sessions(id), revision bigint NOT NULL,
 generation bigint NOT NULL CHECK(generation>0), commitment text NOT NULL CHECK(commitment ~ '^[0-9a-f]{64}$'),
 expires_ms bigint NOT NULL, key_id text NOT NULL, environment text NOT NULL, epoch text NOT NULL
);
-- Updates only via issuer CAS; runtime has no table or issuer grants.
CREATE FUNCTION synthetic_state.evidence_anchor(sid text,rev bigint,previous bigint,commitment text,kid text,deadline bigint,env text,ep text) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE s synthetic_state.sessions%ROWTYPE; old synthetic_state.evidence_anchors%ROWTYPE; p synthetic_state.evidence_policy%ROWTYPE;
BEGIN
 PERFORM synthetic_state.finance_guard();
 SELECT * INTO STRICT p FROM synthetic_state.evidence_policy WHERE id=1;
 SELECT * INTO STRICT s FROM synthetic_state.sessions WHERE id=sid;
 IF env<>p.environment OR ep<>p.epoch OR p.version<>'52-encrypted-shared-evidence-local-v1'
 OR s.revoked OR s.revision<>rev OR s.expires<=synthetic_state.protocol_now()
 OR deadline>floor(extract(epoch FROM s.expires)*1000)::bigint
 OR deadline<=floor(extract(epoch FROM clock_timestamp())*1000)::bigint
 OR kid !~ '^[a-zA-Z0-9_-]{1,40}$' OR commitment !~ '^[0-9a-f]{64}$' OR previous<0
 THEN RAISE EXCEPTION 'evidence_anchor'; END IF;
 SELECT * INTO old FROM synthetic_state.evidence_anchors WHERE session=sid;
 IF (FOUND AND (old.generation<>previous OR deadline>old.expires_ms)) OR (NOT FOUND AND previous<>0)
 THEN RAISE EXCEPTION 'evidence_cas'; END IF;
 INSERT INTO synthetic_state.evidence_anchors VALUES(sid,rev,previous+1,commitment,deadline,kid,env,ep)
 ON CONFLICT(session) DO UPDATE SET revision=EXCLUDED.revision,generation=EXCLUDED.generation,
 commitment=EXCLUDED.commitment,expires_ms=EXCLUDED.expires_ms,key_id=EXCLUDED.key_id;
 RETURN '{}'::jsonb;
END $$;
CREATE TABLE synthetic_state.evidence_attestations (
 nonce text PRIMARY KEY CHECK(nonce ~ '^[0-9a-f]{64}$'), command text NOT NULL,
 request jsonb NOT NULL, commitment text NOT NULL, expires timestamptz NOT NULL,
 epoch text NOT NULL, UNIQUE(command,request)
);
CREATE TABLE synthetic_state.evidence_attestation_uses (
 nonce text PRIMARY KEY REFERENCES synthetic_state.evidence_attestations(nonce)
);
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON synthetic_state.evidence_attestations FOR EACH ROW EXECUTE FUNCTION synthetic_state.immutable();
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON synthetic_state.evidence_attestation_uses FOR EACH ROW EXECUTE FUNCTION synthetic_state.immutable();
CREATE FUNCTION synthetic_state.evidence_attest(n text,a text,p jsonb,hash text,env text,ep text) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE anchor synthetic_state.evidence_anchors%ROWTYPE; cfg synthetic_state.evidence_policy%ROWTYPE;
BEGIN
 PERFORM synthetic_state.finance_guard();
 SELECT * INTO STRICT cfg FROM synthetic_state.evidence_policy WHERE id=1;
 SELECT * INTO STRICT anchor FROM synthetic_state.evidence_anchors WHERE session=p->>'session';
 IF a NOT IN ('reserve','dispatch') OR a IS NULL OR n !~ '^[0-9a-f]{64}$'
 OR env IS DISTINCT FROM cfg.environment OR ep IS DISTINCT FROM cfg.epoch
 OR anchor.epoch<>ep OR anchor.revision IS DISTINCT FROM (p->>'revision')::bigint
 OR hash IS DISTINCT FROM anchor.commitment OR anchor.expires_ms<=floor(extract(epoch FROM clock_timestamp())*1000)::bigint
 THEN RAISE EXCEPTION 'evidence_attestation'; END IF;
 PERFORM synthetic_state.protocol('read',p-ARRAY['capability','operation','ordinal','payload_digest']);
 INSERT INTO synthetic_state.evidence_attestations VALUES(n,a,p,hash,
   least(clock_timestamp()+interval '5 seconds',to_timestamp(anchor.expires_ms/1000.0)),ep);
END $$;
CREATE FUNCTION synthetic_state.evidence_protocol(a text,p jsonb,env text,ep text,proof text) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE cfg synthetic_state.evidence_policy%ROWTYPE; s synthetic_state.sessions%ROWTYPE; anchor synthetic_state.evidence_anchors%ROWTYPE; grant_row synthetic_state.evidence_attestations%ROWTYPE; result jsonb; requested_ttl bigint;
BEGIN
 PERFORM synthetic_state.finance_guard();
 SELECT * INTO STRICT cfg FROM synthetic_state.evidence_policy WHERE id=1;
 IF env IS DISTINCT FROM cfg.environment OR ep IS DISTINCT FROM cfg.epoch OR cfg.version<>'52-encrypted-shared-evidence-local-v1'
 THEN RAISE EXCEPTION 'restore_epoch'; END IF;
 IF a='evidence_clock' THEN
   IF p IS DISTINCT FROM '{}'::jsonb THEN RAISE EXCEPTION 'arguments'; END IF;
   RETURN jsonb_build_object('now_ms',floor(extract(epoch FROM clock_timestamp())*1000)::bigint);
 END IF;
 IF a IN ('create','revise') THEN
   IF p->>'kind' IS DISTINCT FROM 'provider_action' OR jsonb_typeof(p->'payload') IS DISTINCT FROM 'object'
   OR (SELECT count(*) FROM jsonb_object_keys(p->'payload'))<>4
   OR NOT (p->'payload' ?& ARRAY['purpose','sourceDigest','interpretationDigest','requestRevision'])
   OR coalesce(p->'payload'->>'purpose','') NOT IN ('ordinary','advanced','pending','options','lookup','area','details','refresh')
   OR jsonb_typeof(p->'payload'->'sourceDigest') IS DISTINCT FROM 'string'
   OR jsonb_typeof(p->'payload'->'interpretationDigest') IS DISTINCT FROM 'string'
   OR coalesce(p->'payload'->>'sourceDigest','') !~ '^[0-9a-f]{64}$'
   OR coalesce(p->'payload'->>'interpretationDigest','') !~ '^[0-9a-f]{64}$'
   OR NOT synthetic_state.valid_integer(p->'payload'->'requestRevision',1,1000000000000)
   THEN RAISE EXCEPTION 'private_sql_payload_forbidden'; END IF;
 END IF;
 IF a='create' AND synthetic_state.valid_integer(p->'ttl',601,1800) THEN
   IF coalesce(p->'payload'->>'purpose','') NOT IN ('details','refresh') THEN RAISE EXCEPTION 'expiry'; END IF;
   requested_ttl:=(p->>'ttl')::bigint;
   p:=jsonb_set(p,'{ttl}','600'::jsonb);
 END IF;
 IF a='evidence_meta' THEN
   result:=synthetic_state.bridge_protocol('read',p);
   SELECT * INTO STRICT s FROM synthetic_state.sessions WHERE id=p->>'session';
   SELECT * INTO anchor FROM synthetic_state.evidence_anchors WHERE session=s.id;
   IF anchor.session IS NOT NULL AND anchor.expires_ms<=floor(extract(epoch FROM clock_timestamp())*1000)::bigint THEN RAISE EXCEPTION 'evidence_expired'; END IF;
   RETURN jsonb_build_object('budget',(SELECT jsonb_build_object('outing',b.outing,'root',o.root) FROM synthetic_state.budget_bindings b JOIN synthetic_state.budget_outings o ON o.id=b.outing WHERE b.session=s.id),'session',s.id,'revision',s.revision,'binding',s.binding,
       'expires_ms',floor(extract(epoch FROM s.expires)*1000)::bigint,'anchor',CASE WHEN anchor.session IS NULL THEN NULL ELSE to_jsonb(anchor) END,
       'action',result->'payload');
 END IF;
 IF a IN ('reserve','dispatch') THEN
   SELECT * INTO STRICT anchor FROM synthetic_state.evidence_anchors WHERE session=p->>'session';
   IF anchor.revision IS DISTINCT FROM (p->>'revision')::bigint OR anchor.environment<>env OR anchor.epoch<>ep
   OR anchor.expires_ms<=floor(extract(epoch FROM clock_timestamp())*1000)::bigint
   THEN RAISE EXCEPTION 'evidence_proof'; END IF;
   SELECT * INTO STRICT grant_row FROM synthetic_state.evidence_attestations WHERE nonce=proof;
   IF grant_row.command<>a OR grant_row.request<>p OR grant_row.epoch<>ep
   OR grant_row.commitment<>anchor.commitment OR grant_row.expires<=clock_timestamp()
   THEN RAISE EXCEPTION 'evidence_attestation'; END IF;
   INSERT INTO synthetic_state.evidence_attestation_uses VALUES(proof);
 END IF;
 result:=synthetic_state.bridge_protocol(a,p);
 IF requested_ttl IS NOT NULL THEN
   UPDATE synthetic_state.sessions SET expires=expires+(requested_ttl-600)*interval '1 second' WHERE id=p->>'session';
 END IF;
 RETURN result;
END $$;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA synthetic_state FROM PUBLIC,whereto_synthetic_worker;
REVOKE ALL ON ALL TABLES IN SCHEMA synthetic_state FROM PUBLIC,whereto_synthetic_worker;
GRANT EXECUTE ON FUNCTION synthetic_state.evidence_protocol(text,jsonb,text,text,text) TO whereto_synthetic_worker;
GRANT EXECUTE ON FUNCTION synthetic_state.evidence_anchor(text,bigint,bigint,text,text,bigint,text,text) TO whereto_synthetic_issuer;
-- Regrant the unchanged issuer routines revoked above.
GRANT EXECUTE ON FUNCTION synthetic_state.register_action(text,text,text,text) TO whereto_synthetic_issuer;

GRANT EXECUTE ON FUNCTION synthetic_state.evidence_attest(text,text,jsonb,text,text,text) TO whereto_synthetic_issuer;
