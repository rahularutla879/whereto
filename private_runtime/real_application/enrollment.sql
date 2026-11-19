-- Independent witness administrator enrolls exact role configuration AFTER reviews.
-- No rows, credentials, rates, grants, epochs or approvals are inserted here.
CREATE TABLE provider_witness.runtime_enrollment(principal name NOT NULL,configuration text NOT NULL CHECK(configuration~'^[a-f0-9]{64}$'),build text NOT NULL CHECK(build~'^[a-f0-9]{64}$'),epoch text NOT NULL CHECK(epoch~'^[a-f0-9]{64}$'),expires timestamptz NOT NULL,approvals jsonb NOT NULL,PRIMARY KEY(principal,configuration));
REVOKE ALL ON provider_witness.runtime_enrollment FROM PUBLIC;
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON provider_witness.runtime_enrollment FOR EACH ROW EXECUTE FUNCTION provider_rules.immutable();
CREATE FUNCTION provider_witness.assert_runtime(cfg text,b text,ep text,source text) RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE e provider_witness.runtime_enrollment%ROWTYPE;r jsonb;k text;
BEGIN
 SELECT * INTO STRICT e FROM provider_witness.runtime_enrollment WHERE principal=session_user AND configuration=cfg;r:=provider_rules.current_rates();
 IF EXISTS(SELECT 1 FROM provider_witness.events) THEN RAISE EXCEPTION 'runtime_stopped';END IF;
 IF e.configuration IS DISTINCT FROM cfg OR e.build IS DISTINCT FROM b OR e.epoch IS DISTINCT FROM ep OR ep IS DISTINCT FROM provider_witness.epoch() OR e.expires<=clock_timestamp() OR jsonb_typeof(e.approvals)<>'object' OR (SELECT count(*) FROM jsonb_object_keys(e.approvals))<>7 THEN RAISE EXCEPTION 'runtime_enrollment';END IF;
 FOREACH k IN ARRAY ARRAY['qualification','pricing','financial','credentials','content','security','source'] LOOP
 IF coalesce(e.approvals->>k,'')!~'^[a-f0-9]{64}$' THEN RAISE EXCEPTION 'runtime_approval';END IF;END LOOP;
 IF e.approvals->>'source' IS DISTINCT FROM source OR e.approvals->>'financial' IS DISTINCT FROM (SELECT encode(sha256(convert_to(grant_doc::text,'UTF8')),'hex') FROM provider_rules.configuration WHERE id=1) THEN RAISE EXCEPTION 'runtime_authority_binding';END IF;
 IF e.approvals->>'qualification' IS DISTINCT FROM r->>'qualification_evidence' OR e.approvals->>'pricing' IS DISTINCT FROM r->>'price_evidence' THEN RAISE EXCEPTION 'runtime_review_binding';END IF;
END $$;
REVOKE ALL ON FUNCTION provider_witness.assert_runtime(text,text,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION provider_witness.assert_runtime(text,text,text,text) TO real_backend_auth,real_factory_witness,real_counter_witness_client,real_dispatch_witness,real_recovery_client;
