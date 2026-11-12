-- Independent synthetic database/volume. No operational worker credentials/grants.
CREATE SCHEMA witness;
REVOKE ALL ON SCHEMA witness FROM PUBLIC;
CREATE TABLE witness.epochs(sequence bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,epoch text UNIQUE NOT NULL CHECK(epoch ~ '^[0-9a-f]{64}$'));
CREATE TABLE witness.events(sequence bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,kind text NOT NULL CHECK(kind IN ('REVOKED','QUARANTINED','RECONCILED_STOPPED')),reason text NOT NULL);
CREATE TABLE witness.claims(id text PRIMARY KEY,phase text NOT NULL CHECK(phase IN ('reserve','dispatch','deliver','outcome')),quote jsonb NOT NULL,charge bigint NOT NULL CHECK(charge>=0),provider text NOT NULL,day date NOT NULL,outing uuid NOT NULL);
CREATE TABLE witness.confirmations(id text PRIMARY KEY REFERENCES witness.claims(id));
CREATE TABLE witness.outcomes(operation uuid PRIMARY KEY,state text NOT NULL CHECK(state IN ('SUCCEEDED','FAILED','UNCERTAIN')));
DO $$DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['epochs','events','claims','confirmations','outcomes'] LOOP
 EXECUTE format('CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON witness.%I FOR EACH ROW EXECUTE FUNCTION grant_rules.immutable()',t);END LOOP;
END $$;
CREATE FUNCTION witness.operator(a text,p jsonb) RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 PERFORM pg_advisory_xact_lock(527300311);
 PERFORM id FROM grant_rules.configuration WHERE id=1 FOR UPDATE;
 IF a='epoch' AND p ? 'epoch' AND coalesce(p->>'epoch','') ~ '^[0-9a-f]{64}$' THEN
   IF EXISTS(SELECT 1 FROM witness.epochs) THEN INSERT INTO witness.events(kind,reason) VALUES('QUARANTINED','epoch_rotation_full_grant'); END IF;
   INSERT INTO witness.epochs(epoch) VALUES(p->>'epoch');
 ELSIF a IN ('REVOKED','QUARANTINED','RECONCILED_STOPPED') AND length(p->>'reason') BETWEEN 1 AND 100 THEN
   INSERT INTO witness.events(kind,reason) VALUES(a,p->>'reason');
 ELSE RAISE EXCEPTION 'operator_scope'; END IF;
END $$;
CREATE FUNCTION witness.protocol(a text,p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE g jsonb; ep text; expected jsonb; result jsonb; q jsonb; price bigint; active bigint; used record; identifier text;
BEGIN
 IF current_setting('transaction_isolation')<>'read committed' THEN RAISE EXCEPTION 'isolation'; END IF;
 SELECT grant_doc INTO STRICT g FROM grant_rules.configuration WHERE id=1 FOR UPDATE;
 SELECT epoch INTO STRICT ep FROM witness.epochs ORDER BY sequence DESC LIMIT 1;
 IF a='epoch' AND p='{}'::jsonb THEN RETURN jsonb_build_object('epoch',ep); END IF;
 IF a='status' AND p='{}'::jsonb THEN
   RETURN jsonb_build_object('epoch',ep,'quarantined',EXISTS(SELECT 1 FROM witness.events),'gross',(SELECT coalesce(sum(charge),0) FROM witness.claims),'quarantineExposure',CASE WHEN EXISTS(SELECT 1 FROM witness.events) THEN (g->>'total')::bigint ELSE 0 END,'pending',(SELECT count(*) FROM witness.claims c WHERE NOT EXISTS(SELECT 1 FROM witness.confirmations WHERE id=c.id)),'claims',(SELECT count(*) FROM witness.claims)); END IF;
 IF a='quarantine' THEN INSERT INTO witness.events(kind,reason) VALUES('QUARANTINED','service_inconsistency');RETURN '{}'::jsonb; END IF;
 IF EXISTS(SELECT 1 FROM witness.events) OR ep IS DISTINCT FROM g->>'epoch' OR grant_rules.now_at()>=(g->>'expires')::timestamptz THEN RETURN jsonb_build_object('denied','grant_stopped'); END IF;
 IF a='outcome' THEN
   IF p->>'state' NOT IN ('SUCCEEDED','FAILED','UNCERTAIN') OR p->>'state' IS NULL
    OR NOT EXISTS(SELECT 1 FROM witness.claims WHERE id='reserve:'||(p->>'operation')) THEN RAISE EXCEPTION 'outcome'; END IF;
   SELECT quote||jsonb_build_object('state',p->>'state') INTO STRICT q FROM witness.claims WHERE id='reserve:'||(p->>'operation');
   identifier:='outcome:'||(p->>'operation');
   INSERT INTO witness.outcomes VALUES((p->>'operation')::uuid,p->>'state');
   INSERT INTO witness.claims VALUES(identifier,'outcome',q,0,q->>'provider',(q->>'day')::date,(q->>'outing')::uuid);
   INSERT INTO witness.confirmations VALUES(identifier);
   IF p->'observed' IS DISTINCT FROM (SELECT coalesce(jsonb_object_agg(id,sha256(convert_to(quote::text,'UTF8'))::text),'{}'::jsonb) FROM witness.claims) THEN
     INSERT INTO witness.events(kind,reason) VALUES('QUARANTINED','outcome_prefix');RETURN jsonb_build_object('denied','outcome_disagreement');
   END IF;
   RETURN '{}'::jsonb;
 END IF;

 SELECT coalesce(jsonb_object_agg(c.id,sha256(convert_to(c.quote::text,'UTF8'))::text),'{}'::jsonb) INTO expected
 FROM witness.claims c JOIN witness.confirmations f ON f.id=c.id;
 IF p->'observed' IS DISTINCT FROM expected OR EXISTS(SELECT 1 FROM witness.claims c WHERE NOT EXISTS(SELECT 1 FROM witness.confirmations WHERE id=c.id)) THEN
   IF a='confirm' AND p->'observed' IS NOT DISTINCT FROM (SELECT coalesce(jsonb_object_agg(id,sha256(convert_to(quote::text,'UTF8'))::text),'{}'::jsonb) FROM witness.claims) THEN
     INSERT INTO witness.confirmations SELECT id FROM witness.claims c WHERE NOT EXISTS(SELECT 1 FROM witness.confirmations WHERE id=c.id);
     RETURN '{}'::jsonb;
   END IF;
   INSERT INTO witness.events(kind,reason) VALUES('QUARANTINED','prefix_or_uncertainty');RETURN jsonb_build_object('denied','full_grant_quarantine');
 END IF;
 IF a='confirm' THEN RETURN '{}'::jsonb; END IF;
 q:=p->'quote';identifier:=p->>'id';
 IF a NOT IN ('reserve','dispatch','deliver') OR identifier IS DISTINCT FROM (a||':'||(q->>'operation')||(CASE WHEN a='reserve' THEN '' ELSE ':'||(p->>'ordinal') END))
 OR q->>'epoch' IS DISTINCT FROM ep THEN RAISE EXCEPTION 'witness_command'; END IF;
 price:=0;
 IF a='reserve' THEN
   SELECT coalesce(sum(charge),0) t,coalesce(sum(charge) FILTER(WHERE provider=q->>'provider'),0) p,
    coalesce(sum(charge) FILTER(WHERE day=(q->>'day')::date),0) d,coalesce(sum(charge) FILTER(WHERE outing=(q->>'outing')::uuid),0) o,count(*) n INTO used FROM witness.claims WHERE phase='reserve';
   SELECT count(*) INTO active FROM witness.claims c WHERE c.phase='reserve' AND NOT EXISTS(SELECT 1 FROM witness.outcomes WHERE operation=(c.quote->>'operation')::uuid AND state IN ('SUCCEEDED','FAILED'));
   PERFORM grant_rules.check_limit(q,used.t,used.p,used.d,used.o,used.n,active);price:=(q->>'charge')::bigint;
 ELSE
   IF NOT EXISTS(SELECT 1 FROM witness.claims WHERE id='reserve:'||(q->>'operation') AND quote=q)
    OR NOT EXISTS(SELECT 1 FROM witness.confirmations WHERE id='reserve:'||(q->>'operation'))
    OR (p->>'ordinal')::int NOT BETWEEN 1 AND jsonb_array_length(q->'lines') THEN RAISE EXCEPTION 'dispatch_scope'; END IF;
   IF a='deliver' AND NOT EXISTS(SELECT 1 FROM witness.confirmations WHERE id='dispatch:'||(q->>'operation')||':'||(p->>'ordinal')) THEN RAISE EXCEPTION 'intent_before_send'; END IF;
 END IF;
 INSERT INTO witness.claims VALUES(identifier,a,q,price,q->>'provider',(q->>'day')::date,(q->>'outing')::uuid);
 RETURN jsonb_build_object('accepted',identifier);
END $$;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA witness FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA witness FROM PUBLIC;
GRANT USAGE ON SCHEMA witness TO synthetic_witness_service,synthetic_witness_reader,synthetic_grant_operator;
GRANT EXECUTE ON FUNCTION witness.protocol(text,jsonb) TO synthetic_witness_service;
CREATE FUNCTION witness.epoch() RETURNS text LANGUAGE sql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$ SELECT epoch FROM witness.epochs ORDER BY sequence DESC LIMIT 1 $$;
REVOKE ALL ON FUNCTION witness.epoch() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION witness.epoch() TO synthetic_witness_reader;
GRANT EXECUTE ON FUNCTION witness.operator(text,jsonb) TO synthetic_grant_operator;
