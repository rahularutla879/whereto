CREATE TABLE witness.service_nonces(service text NOT NULL,caller text NOT NULL,nonce text NOT NULL,request text NOT NULL,expires bigint NOT NULL,PRIMARY KEY(service,caller,nonce));
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON witness.service_nonces FOR EACH ROW EXECUTE FUNCTION grant_rules.immutable();
CREATE FUNCTION witness.service_nonce(s text,c text,n text,h text,x bigint) RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 IF s IS DISTINCT FROM (CASE session_user WHEN 'synthetic_recovery_client' THEN 'recovery' WHEN 'synthetic_factory_witness' THEN 'factory' WHEN 'synthetic_dispatch_witness' THEN 'dispatcher' WHEN 'synthetic_counter_witness' THEN 'counter' END) OR n!~'^[a-f0-9]{32}$' OR h!~'^[a-f0-9]{64}$' OR length(c) NOT BETWEEN 1 AND 40
 OR x<=floor(extract(epoch FROM clock_timestamp())*1000)::bigint OR x>floor(extract(epoch FROM clock_timestamp())*1000)::bigint+65000 THEN RAISE EXCEPTION 'recovery_nonce';END IF;
 PERFORM pg_advisory_xact_lock(527300312);IF (SELECT count(*) FROM witness.service_nonces)>=10000 THEN RAISE EXCEPTION 'nonce_bound';END IF;
 INSERT INTO witness.service_nonces VALUES(s,c,n,h,x);
END $$;
CREATE FUNCTION witness.service_protocol(a text,p jsonb) RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 IF session_user='synthetic_factory_witness' AND a IN ('epoch','status','confirm','reserve','dispatch','outcome','quarantine','checkpoint') THEN RETURN witness.native_protocol(a,p);END IF;
 IF session_user='synthetic_dispatch_witness' AND a IN ('epoch','status','confirm','deliver','quarantine') THEN RETURN witness.protocol(a,p);END IF;
 RAISE EXCEPTION 'witness_service_role';
END $$;
REVOKE ALL ON FUNCTION witness.service_nonce(text,text,text,text,bigint),witness.service_protocol(text,jsonb) FROM PUBLIC;
GRANT USAGE ON SCHEMA witness TO synthetic_factory_witness,synthetic_dispatch_witness,synthetic_recovery_client;
GRANT EXECUTE ON FUNCTION witness.service_protocol(text,jsonb),witness.epoch() TO synthetic_factory_witness,synthetic_dispatch_witness;
GRANT EXECUTE ON FUNCTION witness.service_nonce(text,text,text,text,bigint),witness.epoch(),witness.operator(text,jsonb) TO synthetic_recovery_client;

GRANT USAGE ON SCHEMA witness TO synthetic_counter_witness;
GRANT EXECUTE ON FUNCTION witness.epoch() TO synthetic_counter_witness;

GRANT EXECUTE ON FUNCTION witness.service_nonce(text,text,text,text,bigint) TO synthetic_factory_witness,synthetic_dispatch_witness,synthetic_counter_witness;
