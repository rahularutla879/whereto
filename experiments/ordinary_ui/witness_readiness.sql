CREATE FUNCTION witness.ui_snapshot(ep text) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 IF ep IS DISTINCT FROM (SELECT epoch FROM witness.epochs ORDER BY sequence DESC LIMIT 1) OR EXISTS(SELECT 1 FROM witness.events) OR EXISTS(SELECT 1 FROM witness.claims c WHERE NOT EXISTS(SELECT 1 FROM witness.confirmations f WHERE f.id=c.id)) THEN RAISE EXCEPTION 'readiness_witness';END IF;
 RETURN jsonb_build_object('grant',(SELECT sha256(convert_to(jsonb_build_object('grant',grant_doc,'rates',rates)::text,'UTF8'))::text FROM grant_rules.configuration WHERE id=1),'observed',(SELECT coalesce(jsonb_object_agg(id,sha256(convert_to(quote::text,'UTF8'))::text),'{}'::jsonb) FROM witness.claims));
END $$;
REVOKE ALL ON FUNCTION witness.ui_snapshot(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION witness.ui_snapshot(text) TO synthetic_factory_witness;
ALTER FUNCTION witness.ui_snapshot(text) OWNER TO whereto_synthetic_owner;
