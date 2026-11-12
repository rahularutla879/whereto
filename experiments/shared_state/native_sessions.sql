-- Additive synthetic profile. No owner database migration or startup selector.
CREATE TABLE synthetic_state.native_checkpoints(session text PRIMARY KEY REFERENCES synthetic_state.sessions(id),root uuid NOT NULL REFERENCES synthetic_state.budget_roots(id),outing uuid NOT NULL REFERENCES synthetic_state.budget_outings(id),inference text NOT NULL REFERENCES synthetic_state.app_sources(inference),version text NOT NULL CHECK(version='52-native-session-reconstruction-local-v1'));
CREATE TABLE synthetic_state.native_turns(session text NOT NULL REFERENCES synthetic_state.native_checkpoints(session),revision bigint NOT NULL,PRIMARY KEY(session,revision));
CREATE TABLE synthetic_state.native_commits(session text NOT NULL REFERENCES synthetic_state.native_checkpoints(session),revision bigint NOT NULL,commitment text NOT NULL,PRIMARY KEY(session,revision));
CREATE TABLE synthetic_state.native_actions(session text PRIMARY KEY REFERENCES synthetic_state.sessions(id),checkpoint text NOT NULL REFERENCES synthetic_state.native_checkpoints(session),revision bigint NOT NULL,worker uuid NOT NULL,fence bigint NOT NULL);
DO $$DECLARE t text;BEGIN FOREACH t IN ARRAY ARRAY['native_checkpoints','native_turns','native_commits','native_actions'] LOOP
 EXECUTE format('CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON synthetic_state.%I FOR EACH ROW EXECUTE FUNCTION synthetic_state.immutable()',t);END LOOP;END $$;
CREATE FUNCTION synthetic_state.native_enroll(sid text,inf text) RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE src synthetic_state.app_sources%ROWTYPE;s synthetic_state.sessions%ROWTYPE;e synthetic_state.evidence%ROWTYPE;
BEGIN
 PERFORM synthetic_state.finance_guard();SELECT * INTO STRICT src FROM synthetic_state.app_sources WHERE inference=inf;
 SELECT * INTO STRICT s FROM synthetic_state.sessions WHERE id=sid;SELECT * INTO STRICT e FROM synthetic_state.evidence WHERE session=sid;
 IF s.revoked OR s.expires<=clock_timestamp() OR e.payload->>'sourceDigest' IS DISTINCT FROM src.source_digest THEN RAISE EXCEPTION 'native_source'; END IF;
 PERFORM synthetic_state.app_enroll_budget(sid,src.root,src.outing);
 INSERT INTO synthetic_state.native_checkpoints VALUES(sid,src.root,src.outing,inf,'52-native-session-reconstruction-local-v1');
END $$;
CREATE FUNCTION synthetic_state.native_quote(p jsonb) RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
DECLARE s synthetic_state.sessions%ROWTYPE;n synthetic_state.native_checkpoints%ROWTYPE;a synthetic_state.evidence_anchors%ROWTYPE;g jsonb;
BEGIN
 PERFORM synthetic_state.protocol('read',p);SELECT * INTO STRICT s FROM synthetic_state.sessions WHERE id=p->>'session';
 SELECT * INTO STRICT n FROM synthetic_state.native_checkpoints WHERE session=s.id;SELECT * INTO STRICT a FROM synthetic_state.evidence_anchors WHERE session=s.id;
 SELECT grant_doc INTO STRICT g FROM grant_rules.configuration WHERE id=1;
 IF n.version<>'52-native-session-reconstruction-local-v1' OR a.revision<>s.revision OR a.expires_ms<=floor(extract(epoch FROM clock_timestamp())*1000)::bigint THEN RAISE EXCEPTION 'native_anchor'; END IF;
 RETURN jsonb_build_object('session',s.id,'revision',s.revision,'worker',s.worker,'fence',s.fence,'commitment',a.commitment,'expires',a.expires_ms,'grant',g->>'id','version',n.version,'epoch',a.epoch,'root',n.root,'outing',n.outing,'provider','synthetic_maps','day',(grant_rules.now_at() AT TIME ZONE (g->>'timezone'))::date);
END $$;
CREATE FUNCTION synthetic_state.native_commit(p jsonb,q jsonb) RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE actual jsonb;
BEGIN
 PERFORM synthetic_state.finance_guard();actual:=synthetic_state.native_quote(p);
 IF actual IS DISTINCT FROM q THEN RAISE EXCEPTION 'native_commit_changed'; END IF;
 INSERT INTO synthetic_state.native_commits VALUES(p->>'session',(p->>'revision')::bigint,q->>'commitment');
 INSERT INTO synthetic_state.app_witness_facts VALUES('native:'||(p->>'session')||':'||(p->>'revision'),q);
END $$;
CREATE FUNCTION synthetic_state.native_action(p jsonb,sid text,http text) RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE n synthetic_state.native_checkpoints%ROWTYPE;e synthetic_state.evidence%ROWTYPE;source synthetic_state.evidence%ROWTYPE;s synthetic_state.sessions%ROWTYPE;
BEGIN
 PERFORM synthetic_state.finance_guard();PERFORM synthetic_state.protocol('read',p);
 SELECT * INTO STRICT n FROM synthetic_state.native_checkpoints WHERE session=p->>'session';SELECT * INTO STRICT s FROM synthetic_state.sessions WHERE id=sid;
 SELECT * INTO STRICT e FROM synthetic_state.evidence WHERE session=sid;SELECT * INTO STRICT source FROM synthetic_state.evidence WHERE session=n.session;
 IF source.payload->>'purpose'='details' THEN RAISE EXCEPTION 'native_selection_only'; END IF;
 IF NOT EXISTS(SELECT 1 FROM synthetic_state.native_turns WHERE session=n.session AND revision=(p->>'revision')::bigint)
 OR s.worker IS DISTINCT FROM (p->>'worker')::uuid OR e.payload->>'sourceDigest' IS DISTINCT FROM source.payload->>'sourceDigest'
 OR e.payload->'requestRevision' IS DISTINCT FROM source.payload->'requestRevision' THEN RAISE EXCEPTION 'native_action_binding'; END IF;
 PERFORM synthetic_state.register_action(sid,http,NULL,NULL);
 -- Source/outing ownership is supplied by native_actions, not a forged inference lease.
 INSERT INTO synthetic_state.native_actions VALUES(sid,n.session,(p->>'revision')::bigint,(p->>'worker')::uuid,(p->>'fence')::bigint);
 PERFORM synthetic_state.app_enroll_budget(sid,n.root,n.outing);
END $$;
CREATE FUNCTION synthetic_state.native_protocol(a text,p jsonb,env text,ep text,proof text) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE link synthetic_state.native_actions%ROWTYPE;cp jsonb;result jsonb;
BEGIN
 -- Delegated commands get the unchanged parent guard once at the final call.
 -- Native-only commands must pass it here before their own transitions.
 IF a IN ('native_revise','native_revoke','native_refresh_seen','native_quote','native_ready','native_begin') THEN
  PERFORM synthetic_state.app_protocol('app_observed','{}',env,ep,NULL);
 END IF;
 IF a IN ('revise','revoke') AND EXISTS(SELECT 1 FROM synthetic_state.native_checkpoints WHERE session=p->>'session') THEN RAISE EXCEPTION 'native_leased_transition_required'; END IF;
 IF a IN ('native_revise','native_revoke') THEN
  PERFORM synthetic_state.protocol('read',p-ARRAY['kind','binding','payload']);
  RETURN synthetic_state.app_protocol(CASE a WHEN 'native_revise' THEN 'revise' ELSE 'revoke' END,p-ARRAY['worker','fence'],env,ep,proof);
 END IF;
 IF a='native_refresh_seen' THEN RETURN jsonb_build_object('seen',EXISTS(SELECT 1 FROM synthetic_state.refresh_claims WHERE refresh_key=p->>'key' AND expires>clock_timestamp())); END IF;
 IF a='native_quote' THEN RETURN synthetic_state.native_quote(p); END IF;
 IF a='native_ready' THEN
  PERFORM synthetic_state.protocol('read',p);
  IF NOT EXISTS(SELECT 1 FROM synthetic_state.native_commits c JOIN synthetic_state.evidence_anchors e ON e.session=c.session AND e.revision=c.revision AND e.commitment=c.commitment WHERE c.session=p->>'session' AND c.revision=(p->>'revision')::bigint)
   OR EXISTS(SELECT 1 FROM synthetic_state.native_turns WHERE session=p->>'session' AND revision=(p->>'revision')::bigint) THEN RAISE EXCEPTION 'native_interrupted_or_incomplete'; END IF;
  RETURN '{}'::jsonb;
 END IF;
 IF a='native_begin' THEN
  PERFORM synthetic_state.native_protocol('native_ready',p,env,ep,NULL);
  INSERT INTO synthetic_state.native_turns VALUES(p->>'session',(p->>'revision')::bigint);RETURN '{}'::jsonb;
 END IF;
 SELECT * INTO link FROM synthetic_state.native_actions WHERE session=p->>'session';
 IF FOUND AND a IN ('reserve','dispatch','app_deliver','transition') THEN
  cp:=jsonb_build_object('session',link.checkpoint,'revision',link.revision,'worker',link.worker,'fence',link.fence);
  PERFORM synthetic_state.protocol('read',cp);
  IF NOT EXISTS(SELECT 1 FROM synthetic_state.native_commits c JOIN synthetic_state.evidence_anchors e ON e.session=c.session AND e.revision=c.revision AND e.commitment=c.commitment WHERE c.session=link.checkpoint AND c.revision=link.revision) THEN RAISE EXCEPTION 'native_uncommitted_evidence'; END IF;
 END IF;
 RETURN synthetic_state.app_protocol(a,p,env,ep,proof);
END $$;
REVOKE ALL ON ALL TABLES IN SCHEMA synthetic_state FROM PUBLIC,whereto_synthetic_worker,whereto_synthetic_issuer;
REVOKE ALL ON FUNCTION synthetic_state.native_enroll(text,text),synthetic_state.native_commit(jsonb,jsonb),synthetic_state.native_action(jsonb,text,text),synthetic_state.native_quote(jsonb),synthetic_state.native_protocol(text,jsonb,text,text,text) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION synthetic_state.app_protocol(text,jsonb,text,text,text) FROM whereto_synthetic_worker;
GRANT EXECUTE ON FUNCTION synthetic_state.native_protocol(text,jsonb,text,text,text) TO whereto_synthetic_worker;
GRANT EXECUTE ON FUNCTION synthetic_state.native_enroll(text,text),synthetic_state.native_commit(jsonb,jsonb),synthetic_state.native_action(jsonb,text,text) TO whereto_synthetic_issuer;
