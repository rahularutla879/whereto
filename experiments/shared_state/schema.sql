-- Synthetic local PostgreSQL ONLY. Not a migration for Supabase or saved plans.
CREATE SCHEMA synthetic_state;
REVOKE ALL ON SCHEMA synthetic_state FROM PUBLIC;
CREATE TABLE synthetic_state.policy (
 id integer PRIMARY KEY CHECK(id=1), version text NOT NULL,
 key_fingerprint text NOT NULL, limits jsonb NOT NULL
);
CREATE TABLE synthetic_state.gate (id integer PRIMARY KEY CHECK(id=1));
INSERT INTO synthetic_state.gate VALUES(1);
CREATE TABLE synthetic_state.sessions (
 id text PRIMARY KEY, revision bigint NOT NULL CHECK(revision>0),
 fence bigint NOT NULL DEFAULT 0 CHECK(fence>=0), worker uuid,
 expires timestamptz NOT NULL, revoked boolean NOT NULL DEFAULT false,
 kind text NOT NULL CHECK(kind IN ('ordinary','advanced_handoff','pending_effective','options','selected','advanced_results')),
 binding text NOT NULL CHECK(length(binding)=64)
);
-- Local synthetic substitute for volatile shared storage. NOT approved for real text.
CREATE UNLOGGED TABLE synthetic_state.evidence (
 session text PRIMARY KEY REFERENCES synthetic_state.sessions(id),
 revision bigint NOT NULL, payload jsonb NOT NULL, integrity bytea NOT NULL
);
CREATE TABLE synthetic_state.capabilities (
 id text PRIMARY KEY CHECK(length(id)=64), session text NOT NULL REFERENCES synthetic_state.sessions(id),
 revision bigint NOT NULL, purpose text NOT NULL,
 action uuid NOT NULL, binding text NOT NULL CHECK(length(binding)=64),
 UNIQUE(session,revision,purpose,action)
);
CREATE TABLE synthetic_state.operations (
 id uuid PRIMARY KEY, capability text NOT NULL UNIQUE REFERENCES synthetic_state.capabilities(id),
 session text NOT NULL REFERENCES synthetic_state.sessions(id), revision bigint NOT NULL,
 worker uuid NOT NULL, fence bigint NOT NULL, provider text NOT NULL CHECK(provider IN ('synthetic_ai','synthetic_maps')),
 charge bigint NOT NULL CHECK(charge>=0 AND charge<=1000000000000),
 created timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE TABLE synthetic_state.facts (
 sequence bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 operation uuid NOT NULL REFERENCES synthetic_state.operations(id),
 kind text NOT NULL CHECK(kind IN ('RESERVED','INTENT','SUCCEEDED','FAILED','UNCERTAIN')),
 created timestamptz NOT NULL DEFAULT clock_timestamp(), UNIQUE(operation,kind)
);
CREATE UNIQUE INDEX single_terminal ON synthetic_state.facts(operation)
 WHERE kind IN ('SUCCEEDED','FAILED','UNCERTAIN');
CREATE FUNCTION synthetic_state.immutable() RETURNS trigger LANGUAGE plpgsql AS $$
 BEGIN RAISE EXCEPTION 'immutable synthetic authority record'; END $$;
CREATE TRIGGER no_operation_mutation BEFORE UPDATE OR DELETE ON synthetic_state.operations
 FOR EACH ROW EXECUTE FUNCTION synthetic_state.immutable();
CREATE TRIGGER no_fact_mutation BEFORE UPDATE OR DELETE ON synthetic_state.facts
 FOR EACH ROW EXECUTE FUNCTION synthetic_state.immutable();
CREATE TRIGGER no_cap_mutation BEFORE UPDATE OR DELETE ON synthetic_state.capabilities
 FOR EACH ROW EXECUTE FUNCTION synthetic_state.immutable();
CREATE TRIGGER no_policy_mutation BEFORE UPDATE OR DELETE ON synthetic_state.policy
 FOR EACH ROW EXECUTE FUNCTION synthetic_state.immutable();
