-- Disposable service profile only; not an owner database migration.
CREATE TABLE synthetic_state.service_profile(id int PRIMARY KEY CHECK(id=1),build text NOT NULL,epoch text NOT NULL);
CREATE TABLE synthetic_state.service_routes(route text NOT NULL,revision bigint NOT NULL,owner text NOT NULL,session text NOT NULL REFERENCES synthetic_state.native_checkpoints(session),build text NOT NULL,epoch text NOT NULL,commitment text NOT NULL,expires bigint NOT NULL,mode text NOT NULL CHECK(mode IN ('source','receipt')),PRIMARY KEY(route,revision));
CREATE TABLE synthetic_state.service_turns(route text NOT NULL,revision bigint NOT NULL,PRIMARY KEY(route,revision),FOREIGN KEY(route,revision) REFERENCES synthetic_state.service_routes(route,revision));
DO $$DECLARE t text;BEGIN FOREACH t IN ARRAY ARRAY['service_profile','service_routes','service_turns'] LOOP
 EXECUTE format('CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON synthetic_state.%I FOR EACH ROW EXECUTE FUNCTION synthetic_state.immutable()',t);END LOOP;END $$;
CREATE TABLE synthetic_state.service_inputs(owner text NOT NULL,id uuid NOT NULL,request text NOT NULL,PRIMARY KEY(owner,id));
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON synthetic_state.service_inputs FOR EACH ROW EXECUTE FUNCTION synthetic_state.immutable();
CREATE FUNCTION synthetic_state.service_start(p jsonb) RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 PERFORM synthetic_state.finance_guard();
 IF p->>'owner'!~'^[a-f0-9]{64}$' OR p->>'request'!~'^[a-f0-9]{64}$' OR NOT EXISTS(SELECT 1 FROM synthetic_state.service_profile WHERE build=p->>'build' AND epoch=p->>'epoch') THEN RAISE EXCEPTION 'input_scope';END IF;
 INSERT INTO synthetic_state.service_inputs VALUES(p->>'owner',(p->>'id')::uuid,p->>'request');
END $$;
CREATE FUNCTION synthetic_state.service_route(a text,p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE r synthetic_state.service_routes%ROWTYPE;cfg synthetic_state.service_profile%ROWTYPE;s synthetic_state.sessions%ROWTYPE;anchor synthetic_state.evidence_anchors%ROWTYPE;
BEGIN
 PERFORM synthetic_state.finance_guard();PERFORM pg_advisory_xact_lock(527300313);
 SELECT * INTO STRICT cfg FROM synthetic_state.service_profile WHERE id=1;
 IF p->>'build' IS DISTINCT FROM cfg.build OR p->>'epoch' IS DISTINCT FROM cfg.epoch OR p->>'route' !~ '^[a-f0-9]{64}$' OR p->>'owner' !~ '^[a-f0-9]{64}$' THEN RAISE EXCEPTION 'route_scope';END IF;
 SELECT * INTO r FROM synthetic_state.service_routes WHERE route=p->>'route' ORDER BY revision DESC LIMIT 1;
 IF a='put' THEN
  SELECT * INTO STRICT s FROM synthetic_state.sessions WHERE id=p->>'session';SELECT * INTO STRICT anchor FROM synthetic_state.evidence_anchors WHERE session=s.id;
  IF s.revoked OR s.expires<=clock_timestamp() OR s.revision<>(p->>'revision')::bigint OR anchor.revision<>s.revision OR p->>'commitment'!~'^[a-f0-9]{64}$'
   OR (p->>'expires')::bigint>anchor.expires_ms OR (p->>'expires')::bigint<=floor(extract(epoch FROM clock_timestamp())*1000)::bigint
   OR (r.route IS NOT NULL AND (r.owner<>p->>'owner' OR r.session<>s.id OR r.mode<>p->>'mode' OR s.revision<=r.revision OR (p->>'expires')::bigint>r.expires))
  THEN RAISE EXCEPTION 'route_publication'; END IF;
  INSERT INTO synthetic_state.service_routes VALUES(p->>'route',s.revision,p->>'owner',s.id,cfg.build,cfg.epoch,p->>'commitment',(p->>'expires')::bigint,p->>'mode');RETURN '{}'::jsonb;
 ELSIF a IN ('get','begin') THEN
  IF r.route IS NULL OR r.owner<>p->>'owner' OR r.revision<>(p->>'revision')::bigint OR r.expires<=floor(extract(epoch FROM clock_timestamp())*1000)::bigint THEN RAISE EXCEPTION 'route_owner_revision'; END IF;
  SELECT * INTO STRICT s FROM synthetic_state.sessions WHERE id=r.session;
  IF s.revoked OR s.revision<>r.revision OR s.expires<=clock_timestamp() THEN RAISE EXCEPTION 'route_session';END IF;
  IF a='begin' THEN
   IF r.mode<>'source' THEN RAISE EXCEPTION 'route_selection_only'; END IF;
   INSERT INTO synthetic_state.service_turns VALUES(r.route,r.revision);
  ELSIF r.mode='source' AND EXISTS(SELECT 1 FROM synthetic_state.service_turns WHERE route=r.route AND revision=r.revision) THEN RAISE EXCEPTION 'interrupted_route';END IF;
  RETURN to_jsonb(r);
 END IF;
 RAISE EXCEPTION 'route_method';
END $$;
CREATE FUNCTION synthetic_state.service_dispatch(a text,p jsonb,env text,ep text) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE h text;i text;
BEGIN
 IF a NOT IN ('check','evidence_meta','evidence_clock','app_observed','app_reserved','app_deliver') THEN RAISE EXCEPTION 'dispatch_method'; END IF;
 IF a='app_deliver' THEN
  SELECT http_id,inference_id INTO h,i FROM synthetic_state.bridge_actions WHERE session=p->>'session';
  IF h IS NULL THEN SELECT http,inference INTO h,i FROM synthetic_state.llm_plans WHERE capability=p->>'capability'; END IF;
  IF h IS NULL OR NOT EXISTS(SELECT 1 FROM synthetic_state.admission_leases WHERE id=h AND domain='http' AND worker=(p->>'worker')::uuid AND refs>0)
   OR (NOT EXISTS(SELECT 1 FROM synthetic_state.bridge_actions WHERE session=p->>'session') AND NOT EXISTS(SELECT 1 FROM synthetic_state.admission_leases WHERE id=i AND domain='inference' AND worker=(p->>'worker')::uuid AND refs>0)) THEN RAISE EXCEPTION 'delivery_admission'; END IF;
 END IF;
 RETURN synthetic_state.native_protocol(a,p,env,ep,NULL);
END $$;
CREATE FUNCTION synthetic_state.service_accept_delivery(id text,q jsonb) RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN PERFORM synthetic_state.app_accept(id,'deliver',q);END $$;
REVOKE ALL ON ALL TABLES IN SCHEMA synthetic_state FROM PUBLIC,whereto_synthetic_worker,whereto_synthetic_issuer,synthetic_dispatch_client,synthetic_counter_client;
REVOKE ALL ON FUNCTION synthetic_state.service_route(text,jsonb),synthetic_state.service_dispatch(text,jsonb,text,text),synthetic_state.service_accept_delivery(text,jsonb) FROM PUBLIC;
GRANT USAGE ON SCHEMA synthetic_state TO synthetic_dispatch_client;
GRANT EXECUTE ON FUNCTION synthetic_state.service_route(text,jsonb) TO whereto_synthetic_issuer;
GRANT EXECUTE ON FUNCTION synthetic_state.service_dispatch(text,jsonb,text,text),synthetic_state.service_accept_delivery(text,jsonb) TO synthetic_dispatch_client;

REVOKE ALL ON FUNCTION synthetic_state.service_start(jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION synthetic_state.service_start(jsonb) TO whereto_synthetic_issuer;
