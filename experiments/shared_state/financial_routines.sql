-- No runtime EXECUTE on any helper or issuer. All work is inside the same gate.
CREATE FUNCTION synthetic_state.finance_guard() RETURNS timestamptz LANGUAGE plpgsql
 SET search_path=pg_catalog,pg_temp AS $$
DECLARE p synthetic_state.finance_policy%ROWTYPE; now_at timestamptz; previous timestamptz; k text;
BEGIN
 PERFORM synthetic_state.protocol('snapshot','{}');
 SELECT * INTO STRICT p FROM synthetic_state.finance_policy WHERE id=1;
 IF p.accounting_identity<>'synthetic-local-project-v1' OR p.version<>'52-financial-authority-local-pg-v3' OR p.rate_version<>'development_cost.RATES-2026-11-03-v1'
   OR p.rates<>'{"search_pro":32000,"search_enterprise":35000,"details":20000,"details_pro":17000,"matrix_element":5000,"matrix_pro_element":10000}'::jsonb
   OR NOT EXISTS(SELECT 1 FROM pg_timezone_names WHERE name=p.timezone)
   OR jsonb_typeof(p.settings) IS DISTINCT FROM 'object' OR (SELECT count(*) FROM jsonb_object_keys(p.settings))<>11
   OR NOT (p.settings ?& ARRAY['searches_per_outing','details_per_outing','candidates_per_activity','matrix_elements_per_outing','requests_per_outing','concurrent_requests','retries','requests_per_session','matrix_elements_per_session','matrix_elements_per_minute','lookups_per_session']) THEN RAISE EXCEPTION 'financial_policy'; END IF;
 FOREACH k IN ARRAY ARRAY['searches_per_outing','details_per_outing','matrix_elements_per_outing','requests_per_outing',
   'requests_per_session','matrix_elements_per_session','matrix_elements_per_minute','lookups_per_session'] LOOP
   IF NOT synthetic_state.valid_integer(p.settings->k,0,1500) THEN RAISE EXCEPTION 'financial_policy'; END IF;
 END LOOP;
 IF p.settings->'concurrent_requests' IS DISTINCT FROM '1'::jsonb OR p.settings->'retries' IS DISTINCT FROM '0'::jsonb
  OR NOT synthetic_state.valid_integer(p.settings->'candidates_per_activity',1,100)
  OR (p.settings->>'searches_per_outing')::bigint>10 OR (p.settings->>'details_per_outing')::bigint>6
  OR (p.settings->>'matrix_elements_per_outing')::bigint>300 OR (p.settings->>'requests_per_outing')::bigint>30
  OR (p.settings->>'requests_per_session')::bigint>50 OR (p.settings->>'matrix_elements_per_minute')::bigint>150
  OR (p.settings->>'lookups_per_session')::bigint>10 THEN RAISE EXCEPTION 'financial_policy'; END IF;
 IF (p.profile='bounded' AND (p.daily_limit IS NOT NULL OR p.shared_minute))
  OR (p.profile='exploration' AND (p.daily_limit IS NOT NULL OR NOT p.shared_minute))
  OR (p.profile='ledger_enforced' AND (p.daily_limit IS NULL OR NOT p.shared_minute)) THEN RAISE EXCEPTION 'financial_profile'; END IF;
 now_at:=synthetic_state.protocol_now();
 SELECT last_seen INTO STRICT previous FROM synthetic_state.finance_time WHERE id=1;
 IF now_at IS NULL OR now_at<previous THEN RAISE EXCEPTION 'clock_rollback'; END IF;
 UPDATE synthetic_state.finance_time SET last_seen=now_at WHERE id=1;
 IF EXISTS(SELECT 1 FROM synthetic_state.operations o WHERE
   NOT EXISTS(SELECT 1 FROM synthetic_state.financial_lines l WHERE l.operation=o.id)
   OR o.charge<>(SELECT sum(charge) FROM synthetic_state.financial_lines l WHERE l.operation=o.id)) THEN
   RAISE EXCEPTION 'financial_history'; END IF;
 RETURN now_at;
END $$;

-- Trusted issuer maps validated server state. Runtime cannot call this function.
CREATE FUNCTION synthetic_state.enroll_budget(sid text, root_id uuid, outing_id uuid) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE now_at timestamptz;
BEGIN
 now_at:=synthetic_state.finance_guard();
 IF sid IS NULL OR root_id IS NULL OR outing_id IS NULL OR NOT EXISTS(
 SELECT 1 FROM synthetic_state.sessions WHERE id=sid AND NOT revoked AND expires>now_at)
 THEN RAISE EXCEPTION 'budget_scope'; END IF;
 INSERT INTO synthetic_state.budget_roots VALUES(root_id) ON CONFLICT DO NOTHING;
 INSERT INTO synthetic_state.budget_outings VALUES(outing_id,root_id) ON CONFLICT DO NOTHING;
 IF NOT EXISTS(SELECT 1 FROM synthetic_state.budget_outings WHERE id=outing_id AND root=root_id) THEN RAISE EXCEPTION 'scope_rebind'; END IF;
 INSERT INTO synthetic_state.budget_bindings VALUES(sid,outing_id);
END $$;

CREATE FUNCTION synthetic_state.approve_requests(cap_id text, items jsonb) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE c synthetic_state.capabilities%ROWTYPE; b synthetic_state.budget_bindings%ROWTYPE;
 p synthetic_state.finance_policy%ROWTYPE; item jsonb; n int:=0; sku_name text; amount numeric; op text; variant text; now_at timestamptz;
BEGIN
 now_at:=synthetic_state.finance_guard();
 SELECT * INTO STRICT p FROM synthetic_state.finance_policy WHERE id=1;
 SELECT * INTO STRICT c FROM synthetic_state.capabilities WHERE id=cap_id;
 SELECT * INTO STRICT b FROM synthetic_state.budget_bindings WHERE session=c.session;
 IF NOT EXISTS(SELECT 1 FROM synthetic_state.sessions s WHERE s.id=c.session AND s.revision=c.revision AND NOT s.revoked AND s.expires>now_at)
   OR c.purpose<>'ordinary_plan' OR EXISTS(SELECT 1 FROM synthetic_state.request_plans WHERE capability=cap_id)
   OR jsonb_typeof(items) IS DISTINCT FROM 'array' OR jsonb_array_length(items) NOT BETWEEN 1 AND 64
 THEN RAISE EXCEPTION 'request_plan'; END IF;
 FOR item IN SELECT * FROM jsonb_array_elements(items) LOOP
   IF jsonb_typeof(item) IS DISTINCT FROM 'object' OR (SELECT count(*) FROM jsonb_object_keys(item))<>5
     OR NOT (item ?& ARRAY['operation','request_digest','rows','cols','variant'])
     OR jsonb_typeof(item->'request_digest') IS DISTINCT FROM 'string' OR item->>'request_digest' !~ '^[0-9a-f]{64}$'
     OR NOT synthetic_state.valid_integer(item->'rows',0,1000000000000)
     OR NOT synthetic_state.valid_integer(item->'cols',0,1000000000000) THEN RAISE EXCEPTION 'request_units'; END IF;
   op:=item->>'operation';variant:=item->>'variant';amount:=1;sku_name:=NULL;
   IF op='matrix' THEN
     amount:=(item->>'rows')::numeric*(item->>'cols')::numeric;
     IF amount NOT BETWEEN 1 AND 1000000000000 THEN RAISE EXCEPTION 'matrix_units'; END IF;
     sku_name:=CASE variant WHEN 'walk' THEN 'matrix_element' WHEN 'drive' THEN 'matrix_pro_element' END;
   ELSE
     IF item->>'rows'<>'0' OR item->>'cols'<>'0' THEN RAISE EXCEPTION 'nonmatrix_units'; END IF;
     sku_name:=CASE
       WHEN op='search' AND variant='enterprise' THEN 'search_enterprise'
       WHEN op IN ('search','lookup') AND variant='pro' THEN 'search_pro'
       WHEN op='details' AND variant='essentials' THEN 'details'
       WHEN op='details' AND variant='pro' THEN 'details_pro'
       WHEN op='route' AND variant='none' THEN 'none' END;
     IF op='route' THEN amount:=0; END IF;
   END IF;
   IF sku_name IS NULL OR amount*coalesce((p.rates->>sku_name)::numeric,0)>1000000000000 THEN RAISE EXCEPTION 'sku_or_overflow'; END IF;
   n:=n+1;
   INSERT INTO synthetic_state.request_plans VALUES(cap_id,n,b.outing,op,item->>'request_digest',sku_name,amount::bigint,p.rate_version);
 END LOOP;
END $$;

CREATE FUNCTION synthetic_state.financial_protocol(a text,p jsonb) RETURNS jsonb LANGUAGE plpgsql
SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
#variable_conflict use_column
DECLARE now_at timestamptz; policy synthetic_state.finance_policy%ROWTYPE; b record;
 cap synthetic_state.capabilities%ROWTYPE; sums record; used record; k text;
 total_charge numeric; today date; result jsonb; n bigint; domain_name text; domain_cap int;
 lease_row synthetic_state.admission_leases%ROWTYPE;
BEGIN
 IF a IS NULL OR jsonb_typeof(p) IS DISTINCT FROM 'object' THEN RAISE EXCEPTION 'arguments'; END IF;
 now_at:=synthetic_state.finance_guard();
 SELECT * INTO STRICT policy FROM synthetic_state.finance_policy WHERE id=1;
 today:=(now_at AT TIME ZONE policy.timezone)::date;
 IF a IN ('admit','admission_bind','admission_retain','admission_release') THEN
   IF jsonb_typeof(p) IS DISTINCT FROM 'object' OR NOT (p ?& ARRAY['id','worker'])
     OR jsonb_typeof(p->'id') IS DISTINCT FROM 'string' OR p->>'id' !~ '^[0-9a-f]{64}$'
     OR jsonb_typeof(p->'worker') IS DISTINCT FROM 'string' THEN RAISE EXCEPTION 'admission'; END IF;
   IF a='admit' THEN
     IF (SELECT count(*) FROM jsonb_object_keys(p))<>4 OR p->>'domain' NOT IN ('http','inference') OR p->>'domain' IS NULL
       OR jsonb_typeof(p->'fingerprint') IS DISTINCT FROM 'string' OR p->>'fingerprint' !~ '^[0-9a-f]{64}$' THEN RAISE EXCEPTION 'admission'; END IF;
     domain_name:=p->>'domain';domain_cap:=CASE domain_name WHEN 'http' THEN 16 ELSE 1 END;
     IF (SELECT count(*) FROM synthetic_state.admission_leases WHERE domain=domain_name AND refs>0)>=domain_cap
      OR (SELECT count(*) FROM synthetic_state.admission_leases WHERE domain=domain_name AND admitted_at>now_at-interval '10 seconds')>=240
     THEN RAISE EXCEPTION 'admission_capacity_burst'; END IF;
     INSERT INTO synthetic_state.admission_leases VALUES(p->>'id',domain_name,p->>'fingerprint',(p->>'worker')::uuid,1,now_at);
   ELSE
     SELECT * INTO STRICT lease_row FROM synthetic_state.admission_leases WHERE id=p->>'id';
     IF lease_row.worker IS DISTINCT FROM (p->>'worker')::uuid OR lease_row.refs<=0
       OR (SELECT count(*) FROM jsonb_object_keys(p))<>(CASE WHEN a='admission_bind' THEN 3 ELSE 2 END) THEN RAISE EXCEPTION 'admission_owner'; END IF;
     IF a='admission_bind' THEN
       IF jsonb_typeof(p->'fingerprint') IS DISTINCT FROM 'string' OR p->>'fingerprint' !~ '^[0-9a-f]{64}$'
        OR EXISTS(SELECT 1 FROM synthetic_state.admission_leases WHERE domain=lease_row.domain AND refs>0 AND fingerprint=p->>'fingerprint')
       THEN RAISE EXCEPTION 'admission_duplicate'; END IF;
       UPDATE synthetic_state.admission_leases SET fingerprint=p->>'fingerprint' WHERE id=lease_row.id;
     ELSE
       UPDATE synthetic_state.admission_leases SET refs=refs+CASE WHEN a='admission_retain' THEN 1 ELSE -1 END WHERE id=lease_row.id;
     END IF;
   END IF;
   RETURN '{}'::jsonb;
 ELSIF a='usage' THEN
   IF p<>'{}'::jsonb THEN RAISE EXCEPTION 'arguments'; END IF;
   SELECT coalesce(sum(charge),0) INTO total_charge FROM synthetic_state.financial_lines WHERE calendar_day=today;
   RETURN jsonb_build_object('calendarDay',today,'timezone',policy.timezone,'dayMicrousd',total_charge,
     'dailyLimitMicrousd',policy.daily_limit,'warning',CASE WHEN policy.shared_minute THEN total_charge>=policy.warning ELSE NULL END,'planning_authorized',false);
 ELSIF a='dispatch' THEN
   IF jsonb_typeof(p) IS DISTINCT FROM 'object' OR (SELECT count(*) FROM jsonb_object_keys(p))<>7
     OR NOT (p ?& ARRAY['session','revision','worker','fence','capability','operation','ordinal'])
     OR NOT synthetic_state.valid_integer(p->'ordinal',1,64) THEN RAISE EXCEPTION 'dispatch'; END IF;
   -- The core read revalidates evidence and fence; never trust a previous Python check.
   PERFORM synthetic_state.protocol('read',p-ARRAY['capability','operation','ordinal']);
   IF NOT EXISTS(SELECT 1 FROM synthetic_state.operations o JOIN synthetic_state.financial_lines l ON l.operation=o.id
     WHERE o.id=(p->>'operation')::uuid AND o.session=p->>'session' AND o.revision=(p->>'revision')::bigint
     AND o.worker=(p->>'worker')::uuid AND o.fence=(p->>'fence')::bigint AND o.capability=p->>'capability'
     AND l.ordinal=(p->>'ordinal')::int AND
     (SELECT kind FROM synthetic_state.facts WHERE operation=o.id ORDER BY sequence DESC LIMIT 1)='INTENT')
     OR (p->>'ordinal')::int<>(SELECT count(*)+1 FROM synthetic_state.financial_dispatch WHERE operation=(p->>'operation')::uuid)
   THEN RAISE EXCEPTION 'dispatch_binding'; END IF;
   INSERT INTO synthetic_state.financial_dispatch VALUES((p->>'operation')::uuid,(p->>'ordinal')::int,now_at);
   RETURN '{}'::jsonb;
 ELSIF a='transition' THEN
   IF p->>'state'='SUCCEEDED' AND
      (SELECT count(*) FROM synthetic_state.financial_dispatch WHERE operation=(p->>'operation')::uuid)
      <>(SELECT count(*) FROM synthetic_state.financial_lines WHERE operation=(p->>'operation')::uuid)
   THEN RAISE EXCEPTION 'incomplete_dispatch'; END IF;
   RETURN synthetic_state.protocol(a,p);
 ELSIF a<>'reserve' THEN
   RETURN synthetic_state.protocol(a,p);
 END IF;
 IF jsonb_typeof(p) IS DISTINCT FROM 'object' OR (SELECT count(*) FROM jsonb_object_keys(p))<>6 OR
    NOT (p ?& ARRAY['session','revision','worker','fence','capability','operation']) THEN RAISE EXCEPTION 'reservation_arguments'; END IF;
 PERFORM synthetic_state.protocol('read',p-ARRAY['capability','operation']);
 SELECT * INTO STRICT cap FROM synthetic_state.capabilities WHERE id=p->>'capability';
 SELECT o.id AS outing,o.root INTO STRICT b FROM synthetic_state.budget_bindings bb JOIN synthetic_state.budget_outings o ON o.id=bb.outing WHERE bb.session=p->>'session';
 IF cap.session<>p->>'session' OR cap.revision<>(p->>'revision')::bigint THEN RAISE EXCEPTION 'scope_binding'; END IF;
 IF NOT EXISTS(SELECT 1 FROM synthetic_state.request_plans WHERE capability=cap.id) OR
    EXISTS(SELECT 1 FROM synthetic_state.request_plans WHERE capability=cap.id AND (outing<>b.outing OR rate_version<>policy.rate_version)) THEN RAISE EXCEPTION 'unapproved_plan'; END IF;
 SELECT count(*) req,count(*) FILTER(WHERE operation IN ('search','lookup')) searches,
   count(*) FILTER(WHERE operation='details') details,count(*) FILTER(WHERE operation='lookup') lookups,
   coalesce(sum(units) FILTER(WHERE operation='matrix'),0) elements,
   sum(units::numeric*coalesce((policy.rates->>sku)::numeric,0)) charge INTO sums FROM synthetic_state.request_plans WHERE capability=cap.id;
 total_charge:=sums.charge;
 IF total_charge>1000000000000 THEN RAISE EXCEPTION 'charge_overflow'; END IF;
 SELECT count(*) req,count(*) FILTER(WHERE kind IN ('search','lookup')) searches,
   count(*) FILTER(WHERE kind='details') details,coalesce(sum(units) FILTER(WHERE kind='matrix'),0) elements
   INTO used FROM synthetic_state.financial_lines WHERE outing=b.outing;
 IF used.details+sums.details>(policy.settings->>'details_per_outing')::bigint OR
   (policy.profile<>'exploration' AND (used.req+sums.req>(policy.settings->>'requests_per_outing')::bigint
    OR used.searches+sums.searches>(policy.settings->>'searches_per_outing')::bigint
    OR used.elements+sums.elements>(policy.settings->>'matrix_elements_per_outing')::bigint)) THEN RAISE EXCEPTION 'outing_budget'; END IF;
 SELECT count(*) req,count(*) FILTER(WHERE kind='lookup') lookups,coalesce(sum(units) FILTER(WHERE kind='matrix'),0) elements
   INTO used FROM synthetic_state.financial_lines WHERE root=b.root;
 IF policy.profile<>'exploration' AND (used.req+sums.req>(policy.settings->>'requests_per_session')::bigint
   OR used.lookups+sums.lookups>(policy.settings->>'lookups_per_session')::bigint
   OR used.elements+sums.elements>(policy.settings->>'matrix_elements_per_session')::bigint) THEN RAISE EXCEPTION 'session_budget'; END IF;
 SELECT count(*) INTO n FROM synthetic_state.operations o WHERE EXISTS(SELECT 1 FROM synthetic_state.financial_lines l WHERE l.operation=o.id AND l.root=b.root)
 AND coalesce((SELECT kind FROM synthetic_state.facts WHERE operation=o.id ORDER BY sequence DESC LIMIT 1),'MISSING') NOT IN ('SUCCEEDED','FAILED');
 IF n>=1 THEN RAISE EXCEPTION 'session_concurrency_uncertainty'; END IF;
 -- Both per-root and (where ledger-enabled) all-root rolling 60-second windows.
 FOR n IN 1..(CASE WHEN policy.shared_minute THEN 2 ELSE 1 END) LOOP
   SELECT count(*) FILTER(WHERE kind IN ('search','lookup')) searches,count(*) FILTER(WHERE kind='details') details,
     coalesce(sum(units) FILTER(WHERE kind='matrix'),0) elements INTO used FROM synthetic_state.financial_lines
     WHERE reserved_at>now_at-interval '60 seconds' AND (n=2 OR root=b.root);
   IF used.searches+sums.searches>10 OR used.details+sums.details>10 OR used.elements+sums.elements>
      (CASE WHEN n=2 THEN 150 ELSE (policy.settings->>'matrix_elements_per_minute')::bigint END) THEN RAISE EXCEPTION 'minute_budget'; END IF;
 END LOOP;
 IF policy.daily_limit IS NOT NULL AND (SELECT coalesce(sum(charge),0) FROM synthetic_state.financial_lines WHERE calendar_day=today)+total_charge>policy.daily_limit THEN RAISE EXCEPTION 'daily_budget'; END IF;
 -- Private core remains the only inserter of operation anchors; caller never supplies prices.
 PERFORM synthetic_state.protocol('reserve',p||jsonb_build_object('provider','synthetic_maps','charge',total_charge));
 INSERT INTO synthetic_state.financial_lines
 SELECT (p->>'operation')::uuid,ordinal,b.root,b.outing,operation,request_digest,sku,units,
   coalesce((policy.rates->>sku)::bigint,0),rate_version,units*coalesce((policy.rates->>sku)::bigint,0),'synthetic_maps',policy.version,policy.accounting_identity,'USD',now_at,today,policy.timezone
 FROM synthetic_state.request_plans WHERE capability=cap.id;
 RETURN '{}'::jsonb;
END $$;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA synthetic_state FROM PUBLIC,whereto_synthetic_worker;
REVOKE ALL ON ALL TABLES IN SCHEMA synthetic_state FROM PUBLIC,whereto_synthetic_worker;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA synthetic_state FROM PUBLIC,whereto_synthetic_worker;
GRANT EXECUTE ON FUNCTION synthetic_state.financial_protocol(text,jsonb) TO whereto_synthetic_worker;
GRANT USAGE ON SCHEMA synthetic_state TO whereto_synthetic_issuer;
GRANT EXECUTE ON FUNCTION synthetic_state.enroll_budget(text,uuid,uuid),synthetic_state.approve_requests(text,jsonb) TO whereto_synthetic_issuer;
