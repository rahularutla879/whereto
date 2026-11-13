-- Disposable-only read probes. No financial transition, clock update or session write.
CREATE FUNCTION synthetic_state.ui_snapshot(ep text,b text) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE g jsonb;r jsonb;t timestamptz;used numeric;
BEGIN
 SELECT grant_doc,rates INTO STRICT g,r FROM grant_rules.configuration WHERE id=1;
 PERFORM grant_rules.validate(g,r);
 SELECT coalesce(value,clock_timestamp()) INTO STRICT t FROM grant_rules.test_clock WHERE id=1;
 IF ep IS DISTINCT FROM g->>'epoch' OR t>=(g->>'expires')::timestamptz OR NOT EXISTS(SELECT 1 FROM synthetic_state.service_profile WHERE build=b AND epoch=ep) THEN RAISE EXCEPTION 'readiness_scope'; END IF;
 IF EXISTS(SELECT 1 FROM synthetic_state.operations o WHERE NOT EXISTS(SELECT 1 FROM synthetic_state.financial_lines f WHERE f.operation=o.id) OR o.charge<>(SELECT sum(charge) FROM synthetic_state.financial_lines f WHERE f.operation=o.id)) THEN RAISE EXCEPTION 'readiness_accounting'; END IF;
 SELECT coalesce(sum((quote->>'charge')::numeric),0) INTO used FROM synthetic_state.app_operations;
 IF used>=(g->>'total')::numeric OR (SELECT count(*) FROM synthetic_state.app_operations)>=(g->>'attempts')::bigint THEN RAISE EXCEPTION 'readiness_exhausted';END IF;
 RETURN jsonb_build_object('grant',(SELECT sha256(convert_to(jsonb_build_object('grant',grant_doc,'rates',rates)::text,'UTF8'))::text FROM grant_rules.configuration WHERE id=1),'observed',synthetic_state.app_observed());
END $$;
REVOKE ALL ON FUNCTION synthetic_state.ui_snapshot(text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION synthetic_state.ui_snapshot(text,text) TO whereto_synthetic_issuer;
ALTER FUNCTION synthetic_state.ui_snapshot(text,text) OWNER TO whereto_synthetic_owner;
