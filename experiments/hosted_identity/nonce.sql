CREATE TABLE witness.hosted_nonces(service text NOT NULL,caller text NOT NULL,nonce text NOT NULL,request text NOT NULL,expires bigint NOT NULL,PRIMARY KEY(service,caller,nonce));
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON witness.hosted_nonces FOR EACH ROW EXECUTE FUNCTION grant_rules.immutable();
CREATE FUNCTION witness.hosted_nonce(s text,c text,n text,h text,x bigint) RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 IF s IS DISTINCT FROM (CASE session_user WHEN 'synthetic_backend_auth' THEN 'backend' WHEN 'synthetic_recovery_client' THEN 'recovery' WHEN 'synthetic_factory_witness' THEN 'factory' WHEN 'synthetic_dispatch_witness' THEN 'dispatcher' WHEN 'synthetic_counter_witness' THEN 'counter' END)
 OR n!~'^[a-f0-9]{32}$' OR h!~'^[a-f0-9]{64}$' OR length(c) NOT BETWEEN 1 AND 40 OR x<=floor(extract(epoch FROM clock_timestamp())*1000)::bigint OR x>floor(extract(epoch FROM clock_timestamp())*1000)::bigint+65000 THEN RAISE EXCEPTION 'hosted_nonce_scope';END IF;
 PERFORM pg_advisory_xact_lock(527300314);IF (SELECT count(*) FROM witness.hosted_nonces)>=10000 THEN RAISE EXCEPTION 'nonce_bound';END IF;
 INSERT INTO witness.hosted_nonces VALUES(s,c,n,h,x);
END $$;
REVOKE ALL ON witness.hosted_nonces FROM PUBLIC;
REVOKE ALL ON FUNCTION witness.hosted_nonce(text,text,text,text,bigint) FROM PUBLIC;
GRANT USAGE ON SCHEMA witness TO synthetic_backend_auth;
GRANT EXECUTE ON FUNCTION witness.epoch(),witness.hosted_nonce(text,text,text,text,bigint) TO synthetic_backend_auth,synthetic_factory_witness,synthetic_dispatch_witness,synthetic_counter_witness,synthetic_recovery_client;
