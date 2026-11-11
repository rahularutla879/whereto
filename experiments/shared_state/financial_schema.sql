-- New local fictional DB only. The runtime cannot enroll roots/outings/plans.
CREATE TABLE synthetic_state.finance_policy (
 id integer PRIMARY KEY CHECK(id=1), version text NOT NULL,
 rate_version text NOT NULL, rates jsonb NOT NULL, settings jsonb NOT NULL,
 timezone text NOT NULL, daily_limit bigint CHECK(daily_limit>0),
 warning bigint NOT NULL CHECK(warning>0), shared_minute boolean NOT NULL,
 accounting_identity text NOT NULL CHECK(accounting_identity='synthetic-local-project-v1'),
 profile text NOT NULL CHECK(profile IN ('bounded','exploration','ledger_enforced'))
);
CREATE TABLE synthetic_state.budget_roots (id uuid PRIMARY KEY);
CREATE TABLE synthetic_state.budget_outings (
 id uuid PRIMARY KEY, root uuid NOT NULL REFERENCES synthetic_state.budget_roots(id)
);
CREATE TABLE synthetic_state.budget_bindings (
 session text PRIMARY KEY REFERENCES synthetic_state.sessions(id),
 outing uuid NOT NULL REFERENCES synthetic_state.budget_outings(id)
);
CREATE TABLE synthetic_state.request_plans (
 capability text NOT NULL REFERENCES synthetic_state.capabilities(id), ordinal int NOT NULL CHECK(ordinal BETWEEN 1 AND 64),
 outing uuid NOT NULL REFERENCES synthetic_state.budget_outings(id),
 operation text NOT NULL CHECK(operation IN ('search','lookup','details','matrix','route')),
 request_digest text NOT NULL CHECK(request_digest ~ '^[0-9a-f]{64}$'),
 sku text NOT NULL, units bigint NOT NULL CHECK(units BETWEEN 0 AND 1000000000000),
 rate_version text NOT NULL, PRIMARY KEY(capability,ordinal),
 UNIQUE(capability,operation,request_digest)
);
CREATE TABLE synthetic_state.financial_lines (
 operation uuid NOT NULL REFERENCES synthetic_state.operations(id), ordinal int NOT NULL CHECK(ordinal BETWEEN 1 AND 64),
 root uuid NOT NULL REFERENCES synthetic_state.budget_roots(id),
 outing uuid NOT NULL REFERENCES synthetic_state.budget_outings(id),
 kind text NOT NULL, request_digest text NOT NULL,
 sku text NOT NULL, units bigint NOT NULL CHECK(units>=0), rate bigint NOT NULL CHECK(rate>=0),
 rate_version text NOT NULL, charge bigint NOT NULL CHECK(charge>=0),
 provider text NOT NULL CHECK(provider='synthetic_maps'),
 policy_version text NOT NULL, accounting_identity text NOT NULL, currency text NOT NULL CHECK(currency='USD'),
 reserved_at timestamptz NOT NULL, calendar_day date NOT NULL, timezone text NOT NULL,
 PRIMARY KEY(operation,ordinal), UNIQUE(outing,kind,request_digest)
);
CREATE TABLE synthetic_state.finance_time (id int PRIMARY KEY CHECK(id=1), last_seen timestamptz);
INSERT INTO synthetic_state.finance_time VALUES(1,NULL);
CREATE TABLE synthetic_state.admission_leases (
 id text PRIMARY KEY CHECK(id ~ '^[0-9a-f]{64}$'),
 domain text NOT NULL CHECK(domain IN ('http','inference')),
 fingerprint text NOT NULL CHECK(fingerprint ~ '^[0-9a-f]{64}$'),
 worker uuid NOT NULL, refs int NOT NULL CHECK(refs>=0), admitted_at timestamptz NOT NULL
);
CREATE UNIQUE INDEX active_fingerprint ON synthetic_state.admission_leases(domain,fingerprint) WHERE refs>0;
-- Financial/identity anchors are immutable even through accidental owner DML.
DO $$DECLARE t text; BEGIN
 FOREACH t IN ARRAY ARRAY['finance_policy','budget_roots','budget_outings','budget_bindings','request_plans','financial_lines'] LOOP
   EXECUTE format('CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON synthetic_state.%I FOR EACH ROW EXECUTE FUNCTION synthetic_state.immutable()',t);
 END LOOP;
END $$;
CREATE TABLE synthetic_state.financial_dispatch (
 operation uuid NOT NULL, ordinal int NOT NULL CHECK(ordinal BETWEEN 1 AND 64), dispatched_at timestamptz NOT NULL,
 PRIMARY KEY(operation,ordinal), FOREIGN KEY(operation,ordinal) REFERENCES synthetic_state.financial_lines(operation,ordinal)
);
CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON synthetic_state.financial_dispatch
 FOR EACH ROW EXECUTE FUNCTION synthetic_state.immutable();
