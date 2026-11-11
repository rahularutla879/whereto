-- Installed only by disposable fixture bootstrap under the NOLOGIN owner.
-- No dynamic SQL, caller-controlled search path, public helper, or table grants.
CREATE FUNCTION synthetic_state.valid_integer(v jsonb, lo bigint, hi bigint) RETURNS boolean
LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
 SELECT COALESCE(jsonb_typeof(v)='number' AND v::text ~ '^[0-9]{1,13}$'
   AND (v::text)::numeric BETWEEN lo AND hi,false)
$$;
CREATE FUNCTION synthetic_state.abandon(sid text) RETURNS void
LANGUAGE sql SET search_path=pg_catalog,pg_temp AS $$
 INSERT INTO synthetic_state.facts(operation,kind)
 SELECT o.id,'UNCERTAIN' FROM synthetic_state.operations o WHERE o.session=sid AND
 (SELECT kind FROM synthetic_state.facts f WHERE f.operation=o.id ORDER BY sequence DESC LIMIT 1)
 IN ('RESERVED','INTENT')
$$;
CREATE FUNCTION synthetic_state.protocol(a text, p jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
#variable_conflict use_column
<<authority>>
DECLARE
 policy synthetic_state.policy%ROWTYPE;
 s synthetic_state.sessions%ROWTYPE;
 e synthetic_state.evidence%ROWTYPE;
 cap synthetic_state.capabilities%ROWTYPE;
 op synthetic_state.operations%ROWTYPE;
 total record; active bigint; n bigint; state text; expected text;
 fields text[]; k text; sid text; kind text; binding text; payload jsonb;
 revision bigint; fence bigint; worker uuid; result jsonb;
BEGIN
 -- REPEATABLE READ could retain a pre-lock financial snapshot. No fallback.
 IF current_setting('transaction_isolation')<>'read committed' THEN
   RAISE EXCEPTION 'isolation' USING ERRCODE='P0001'; END IF;
 PERFORM id FROM synthetic_state.gate WHERE id=1 FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'gate_missing'; END IF;
 SELECT * INTO STRICT policy FROM synthetic_state.policy WHERE id=1;
 IF policy.version<>'52-shared-authority-constrained-pg-v2' THEN
   RAISE EXCEPTION 'policy_identity'; END IF;
 IF jsonb_typeof(policy.limits) IS DISTINCT FROM 'object'
   OR (SELECT count(*) FROM jsonb_object_keys(policy.limits))<>5
   OR NOT (policy.limits ?& ARRAY['gross','provider_gross','attempts','provider_attempts','concurrency'])
   OR policy.key_fingerprint !~ '^[0-9a-f]{64}$' THEN RAISE EXCEPTION 'policy_corrupt'; END IF;
 FOREACH k IN ARRAY ARRAY['gross','provider_gross','attempts','provider_attempts'] LOOP
   IF NOT synthetic_state.valid_integer(policy.limits->k,0,1000000000000) THEN RAISE EXCEPTION 'policy_corrupt'; END IF;
 END LOOP;
 IF NOT synthetic_state.valid_integer(policy.limits->'concurrency',1,16) THEN RAISE EXCEPTION 'policy_corrupt'; END IF;
 IF jsonb_typeof(p) IS DISTINCT FROM 'object' OR a IS NULL THEN RAISE EXCEPTION 'arguments'; END IF;
 fields := CASE a
 WHEN 'check' THEN ARRAY['version','fingerprint','limits']
 WHEN 'snapshot' THEN ARRAY[]::text[]
 WHEN 'create' THEN ARRAY['session','kind','binding','payload','ttl']
 WHEN 'claim' THEN ARRAY['session','revision','worker']
 WHEN 'read' THEN ARRAY['session','revision','worker','fence']
 WHEN 'revise' THEN ARRAY['session','revision','kind','binding','payload']
 WHEN 'revoke' THEN ARRAY['session','revision']
 WHEN 'issue' THEN ARRAY['session','revision','worker','fence','capability','purpose','action']
 WHEN 'reserve' THEN ARRAY['session','revision','worker','fence','capability','operation','provider','charge']
 WHEN 'transition' THEN ARRAY['session','revision','worker','fence','capability','operation','state']
 ELSE NULL END;
 IF fields IS NULL OR (SELECT count(*) FROM jsonb_object_keys(p))<>cardinality(fields)
   OR NOT (p ?& fields) THEN RAISE EXCEPTION 'arguments'; END IF;
 -- Missing or inconsistent facts can never free financial capacity.
 IF EXISTS(SELECT 1 FROM synthetic_state.operations o WHERE
   NOT EXISTS(SELECT 1 FROM synthetic_state.facts f WHERE f.operation=o.id AND f.kind='RESERVED')
   OR (SELECT f.kind FROM synthetic_state.facts f WHERE f.operation=o.id ORDER BY sequence LIMIT 1)<>'RESERVED'
   OR (EXISTS(SELECT 1 FROM synthetic_state.facts f WHERE f.operation=o.id AND f.kind IN ('SUCCEEDED','FAILED'))
      AND NOT EXISTS(SELECT 1 FROM synthetic_state.facts f WHERE f.operation=o.id AND f.kind='INTENT')))
 THEN RAISE EXCEPTION 'operation_facts_corrupt'; END IF;
 IF a='check' THEN
   IF p->>'version' IS DISTINCT FROM policy.version OR p->>'fingerprint' IS DISTINCT FROM policy.key_fingerprint
      OR p->'limits' IS DISTINCT FROM policy.limits THEN RAISE EXCEPTION 'policy_identity'; END IF;
   RETURN '{}'::jsonb;
 END IF;
 IF a='snapshot' THEN
   SELECT count(*) AS attempts,coalesce(sum(charge),0) AS gross INTO total FROM synthetic_state.operations;
   SELECT coalesce(jsonb_object_agg(x.kind,x.n),'{}'::jsonb) INTO result FROM
      (SELECT last.kind,count(*) n FROM
       (SELECT DISTINCT ON(operation) kind FROM synthetic_state.facts ORDER BY operation,sequence DESC) last
       GROUP BY last.kind) x;
   RETURN jsonb_build_object('attempts',total.attempts,'gross',total.gross,'states',result,'planning_authorized',false);
 END IF;
 sid:=p->>'session';
 IF jsonb_typeof(p->'session') IS DISTINCT FROM 'string' OR sid !~ '^[0-9a-f]{64}$' THEN RAISE EXCEPTION 'session'; END IF;
 IF a IN ('create','revise') THEN
   kind:=p->>'kind';binding:=p->>'binding';payload:=p->'payload';
   IF kind IS NULL OR kind NOT IN ('ordinary','advanced_handoff','pending_effective','options','selected','advanced_results')
     OR jsonb_typeof(p->'binding') IS DISTINCT FROM 'string' OR binding !~ '^[0-9a-f]{64}$'
     OR jsonb_typeof(payload) IS DISTINCT FROM 'object' OR octet_length(payload::text)>131072
   THEN RAISE EXCEPTION 'evidence'; END IF;
 END IF;
 IF a='create' THEN
   IF NOT synthetic_state.valid_integer(p->'ttl',1,600) THEN RAISE EXCEPTION 'expiry'; END IF;
   SELECT count(*) INTO n FROM synthetic_state.sessions WHERE NOT revoked AND expires>clock_timestamp();
   IF n>=50 THEN RAISE EXCEPTION 'session_capacity'; END IF;
   INSERT INTO synthetic_state.sessions(id,revision,expires,kind,binding)
     VALUES(sid,1,clock_timestamp()+(p->>'ttl')::int*interval '1 second',kind,binding);
   INSERT INTO synthetic_state.evidence VALUES(sid,1,payload,sha256(convert_to(payload::text,'UTF8')));
   RETURN '{}'::jsonb;
 END IF;
 IF NOT synthetic_state.valid_integer(p->'revision',1,1000000000000) THEN RAISE EXCEPTION 'revision'; END IF;
 revision:=(p->>'revision')::bigint;
 SELECT * INTO s FROM synthetic_state.sessions WHERE id=sid;
 IF NOT FOUND OR s.expires<=clock_timestamp() OR s.revoked OR s.revision<>revision THEN RAISE EXCEPTION 'session_revision'; END IF;
 IF a IN ('read','issue','reserve','transition') THEN
   IF NOT synthetic_state.valid_integer(p->'fence',1,1000000000000)
     OR jsonb_typeof(p->'worker') IS DISTINCT FROM 'string' THEN RAISE EXCEPTION 'fence'; END IF;
   fence:=(p->>'fence')::bigint;worker:=(p->>'worker')::uuid;
   IF s.fence<>fence OR s.worker IS DISTINCT FROM worker THEN RAISE EXCEPTION 'stale_worker'; END IF;
 END IF;
 IF a<>'revoke' THEN
   SELECT * INTO e FROM synthetic_state.evidence WHERE session=sid;
   IF NOT FOUND OR e.revision<>revision OR e.integrity IS DISTINCT FROM sha256(convert_to(e.payload::text,'UTF8')) THEN
     RAISE EXCEPTION 'evidence_integrity'; END IF;
 END IF;
 IF a='claim' THEN
   IF jsonb_typeof(p->'worker') IS DISTINCT FROM 'string' THEN RAISE EXCEPTION 'worker'; END IF;
   worker:=(p->>'worker')::uuid;
   PERFORM synthetic_state.abandon(sid);
   UPDATE synthetic_state.sessions SET fence=synthetic_state.sessions.fence+1,worker=authority.worker WHERE id=sid RETURNING synthetic_state.sessions.fence INTO fence;
   RETURN jsonb_build_object('fence',fence);
 ELSIF a='read' THEN
   RETURN jsonb_build_object('kind',s.kind,'binding',s.binding,'payload',e.payload);
 ELSIF a='revise' THEN
   PERFORM synthetic_state.abandon(sid);
   UPDATE synthetic_state.sessions SET revision=revision+1,fence=synthetic_state.sessions.fence+1,worker=NULL,
      kind=authority.kind,binding=authority.binding WHERE id=sid;
   UPDATE synthetic_state.evidence SET revision=authority.revision+1,payload=authority.payload,
      integrity=sha256(convert_to(authority.payload::text,'UTF8')) WHERE session=sid;
   IF NOT FOUND THEN RAISE EXCEPTION 'evidence_missing'; END IF;
   RETURN jsonb_build_object('revision',revision+1);
 ELSIF a='revoke' THEN
   PERFORM synthetic_state.abandon(sid);
   UPDATE synthetic_state.sessions SET revoked=true,fence=synthetic_state.sessions.fence+1 WHERE id=sid;
   RETURN '{}'::jsonb;
 ELSIF a='issue' THEN
   expected:=CASE s.kind WHEN 'ordinary' THEN 'ordinary_plan' WHEN 'advanced_handoff' THEN 'handoff_only'
     WHEN 'pending_effective' THEN 'clarify_only' WHEN 'selected' THEN 'save_selection' ELSE 'browse_only' END;
   IF p->>'purpose' IS DISTINCT FROM expected OR jsonb_typeof(p->'capability') IS DISTINCT FROM 'string'
     OR p->>'capability' !~ '^[0-9a-f]{64}$' OR jsonb_typeof(p->'action') IS DISTINCT FROM 'string'
   THEN RAISE EXCEPTION 'purpose_capability'; END IF;
   SELECT count(*) INTO n FROM synthetic_state.capabilities c WHERE c.session=sid AND c.revision=authority.revision;
   IF n>=32 THEN RAISE EXCEPTION 'capability_capacity'; END IF;
   INSERT INTO synthetic_state.capabilities VALUES(p->>'capability',sid,revision,expected,(p->>'action')::uuid,s.binding);
   RETURN '{}'::jsonb;
 END IF;
 IF jsonb_typeof(p->'capability') IS DISTINCT FROM 'string' OR p->>'capability' !~ '^[0-9a-f]{64}$'
   OR jsonb_typeof(p->'operation') IS DISTINCT FROM 'string' THEN RAISE EXCEPTION 'operation'; END IF;
 SELECT * INTO cap FROM synthetic_state.capabilities c WHERE c.id=p->>'capability';
 IF NOT FOUND OR cap.session<>sid OR cap.revision<>revision OR cap.binding<>s.binding THEN RAISE EXCEPTION 'capability_binding'; END IF;
 IF a='reserve' THEN
   IF s.kind<>'ordinary' OR cap.purpose<>'ordinary_plan' THEN RAISE EXCEPTION 'not_provider_ready'; END IF;
   IF p->>'provider' IS NULL OR p->>'provider' NOT IN ('synthetic_ai','synthetic_maps') OR
      NOT synthetic_state.valid_integer(p->'charge',0,1000000000000) THEN RAISE EXCEPTION 'reservation'; END IF;
   SELECT count(*) AS attempts,coalesce(sum(charge),0) AS gross,
     count(*) FILTER(WHERE provider=p->>'provider') AS provider_attempts,
     coalesce(sum(charge) FILTER(WHERE provider=p->>'provider'),0) AS provider_gross
     INTO total FROM synthetic_state.operations;
   SELECT count(*) INTO active FROM synthetic_state.operations o WHERE
     coalesce((SELECT f.kind FROM synthetic_state.facts f WHERE f.operation=o.id ORDER BY sequence DESC LIMIT 1),'MISSING') NOT IN ('SUCCEEDED','FAILED');
   IF total.gross+(p->>'charge')::bigint>(policy.limits->>'gross')::bigint OR
      total.provider_gross+(p->>'charge')::bigint>(policy.limits->>'provider_gross')::bigint OR
      total.attempts+1>(policy.limits->>'attempts')::bigint OR
      total.provider_attempts+1>(policy.limits->>'provider_attempts')::bigint OR
      active>=(policy.limits->>'concurrency')::bigint THEN RAISE EXCEPTION 'budget_or_uncertainty'; END IF;
   INSERT INTO synthetic_state.operations(id,capability,session,revision,worker,fence,provider,charge)
      VALUES((p->>'operation')::uuid,cap.id,sid,revision,worker,fence,p->>'provider',(p->>'charge')::bigint);
   INSERT INTO synthetic_state.facts(operation,kind) VALUES((p->>'operation')::uuid,'RESERVED');
 ELSE
   SELECT * INTO op FROM synthetic_state.operations o WHERE o.id=(p->>'operation')::uuid;
   IF NOT FOUND OR op.session<>sid OR op.revision<>revision OR op.worker<>worker OR op.fence<>fence OR op.capability<>cap.id THEN RAISE EXCEPTION 'operation_binding'; END IF;
   SELECT f.kind INTO state FROM synthetic_state.facts f WHERE f.operation=op.id ORDER BY sequence DESC LIMIT 1;
   IF NOT coalesce((p->>'state'='INTENT' AND state='RESERVED') OR
      (p->>'state' IN ('SUCCEEDED','FAILED') AND state='INTENT') OR
      (p->>'state'='UNCERTAIN' AND state IN ('RESERVED','INTENT')),false) THEN RAISE EXCEPTION 'state_transition'; END IF;
   INSERT INTO synthetic_state.facts(operation,kind) VALUES(op.id,p->>'state');
 END IF;
 RETURN '{}'::jsonb;
END $$;
-- PUBLIC gets EXECUTE on new functions by default: explicitly remove it, including helpers.
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA synthetic_state FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA synthetic_state FROM PUBLIC,whereto_synthetic_worker;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA synthetic_state FROM PUBLIC,whereto_synthetic_worker;
GRANT USAGE ON SCHEMA synthetic_state TO whereto_synthetic_worker;
GRANT EXECUTE ON FUNCTION synthetic_state.protocol(text,jsonb) TO whereto_synthetic_worker;
ALTER DEFAULT PRIVILEGES IN SCHEMA synthetic_state REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;
