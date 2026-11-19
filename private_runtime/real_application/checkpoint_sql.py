"""Finite source-ticket projection. Never installs policy, rates or grants."""
from private_runtime.real_finance.profile import PARENT,namespace,replace,verify
VERSION='52-real-source-ticket-v1'

def scripts():
    verify()
    op=namespace((PARENT/'native_sessions.sql').read_text())
    op=op.replace('52-native-session-reconstruction-local-v1',VERSION)
    op=op.replace('provider_state.app_protocol(', 'provider_state.real_application_protocol(')
    op=op.replace('FUNCTION provider_state.app_protocol(', 'FUNCTION provider_state.real_application_protocol(')
    # Parent quote contains metadata only, not provider responses or prices.
    op+='''
CREATE TABLE provider_state.real_source_owners(session text PRIMARY KEY REFERENCES provider_state.native_checkpoints(session),owner text NOT NULL CHECK(owner ~ '^[0-9a-f]{64}$'),build text NOT NULL CHECK(build ~ '^[0-9a-f]{64}$'),completed uuid NOT NULL REFERENCES provider_state.real_response_receipts(operation));
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON provider_state.real_source_owners FOR EACH ROW EXECUTE FUNCTION provider_state.immutable();
REVOKE ALL ON provider_state.real_source_owners FROM PUBLIC,whereto_real_worker,whereto_real_issuer;
CREATE FUNCTION provider_state.real_source_enroll(sid text,inf text,principal text,build_id text,completed_op uuid) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 PERFORM provider_state.finance_guard();
 IF NOT EXISTS(SELECT 1 FROM provider_state.operations o JOIN provider_state.llm_plans l ON l.capability=o.capability JOIN provider_state.real_response_receipts r ON r.operation=o.id JOIN provider_state.llm_usage u ON u.operation=o.id WHERE o.id=completed_op AND l.inference=inf AND EXISTS(SELECT 1 FROM provider_state.facts f WHERE f.operation=o.id AND f.kind='SUCCEEDED') AND u.valid) THEN RAISE EXCEPTION 'real_source_completed_inference'; END IF;
 PERFORM provider_state.native_enroll(sid,inf);
 INSERT INTO provider_state.real_source_owners VALUES(sid,principal,build_id,completed_op);
END $$;
CREATE FUNCTION provider_state.real_source_owner(sid text,rev bigint,principal text,build_id text) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE result jsonb;
BEGIN
 PERFORM provider_state.finance_guard();
 SELECT jsonb_build_object('completed',n.completed,'root',c.root,'outing',c.outing,'inference',c.inference)
 INTO STRICT result FROM provider_state.real_source_owners n JOIN provider_state.native_checkpoints c ON c.session=n.session JOIN provider_state.sessions s ON s.id=n.session
 WHERE n.session=sid AND n.owner=principal AND n.build=build_id AND s.revision=rev AND NOT s.revoked AND s.expires>clock_timestamp();
 RETURN result;
END $$;
REVOKE ALL ON FUNCTION provider_state.real_source_enroll(text,text,text,text,uuid),provider_state.real_source_owner(text,bigint,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION provider_state.real_source_enroll(text,text,text,text,uuid) TO whereto_real_issuer;
GRANT EXECUTE ON FUNCTION provider_state.real_source_owner(text,bigint,text,text) TO whereto_real_worker;
REVOKE EXECUTE ON FUNCTION provider_state.native_enroll(text,text) FROM whereto_real_issuer;
-- Only the checked source-ticket front door is available to the runtime.
REVOKE EXECUTE ON FUNCTION provider_state.real_application_protocol(text,jsonb,text,text,text) FROM whereto_real_worker;
'''
    wit=namespace((PARENT/'native_witness.sql').read_text()).replace('52-native-session-reconstruction-local-v1',VERSION)
    return {'operational':op,'witness':wit}
