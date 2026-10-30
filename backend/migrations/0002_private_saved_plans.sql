-- Task 49: capability-scoped local backend; no Supabase API-role grants.
ALTER TABLE whereto.plans
  ADD COLUMN access_hash text UNIQUE CHECK (access_hash ~ '^[0-9a-f]{64}$'),
  ADD COLUMN save_fingerprint text CHECK (save_fingerprint ~ '^[0-9a-f]{64}$'),
  ADD COLUMN access_expires_at timestamptz NOT NULL DEFAULT (now() + interval '30 days'),
  ADD COLUMN selected_option integer NOT NULL DEFAULT 0 CHECK (selected_option BETWEEN 0 AND 2);
ALTER TABLE whereto.plan_constraints ADD COLUMN preferences jsonb NOT NULL DEFAULT '{}'
  CHECK (jsonb_typeof(preferences) = 'object');
ALTER TABLE whereto.itinerary_stops ADD COLUMN fictional_snapshot jsonb
  CHECK (fictional_snapshot IS NULL OR jsonb_typeof(fictional_snapshot) = 'object');
ALTER TABLE whereto.generated_itineraries ADD COLUMN fictional_metrics jsonb
  CHECK (fictional_metrics IS NULL OR jsonb_typeof(fictional_metrics) = 'object');

-- Provision a password separately, never in migration history. No membership
-- in administrative roles, no DDL, mutation, delete, ledger or public access.
CREATE ROLE whereto_plan_runtime LOGIN NOINHERIT NOBYPASSRLS NOSUPERUSER NOCREATEDB NOCREATEROLE;
-- Allow only the migration administrator to impersonate this restricted role for rollback tests.
GRANT whereto_plan_runtime TO CURRENT_USER WITH INHERIT FALSE, SET TRUE;
GRANT USAGE ON SCHEMA whereto TO whereto_plan_runtime;
GRANT SELECT, INSERT ON whereto.plans, whereto.plan_constraints,
  whereto.generated_itineraries, whereto.itinerary_stops, whereto.source_metadata TO whereto_plan_runtime;
CREATE POLICY private_plan ON whereto.plans TO whereto_plan_runtime
  USING (access_hash = current_setting('whereto.access_hash', true) AND access_expires_at > now())
  WITH CHECK (access_hash = current_setting('whereto.access_hash', true) AND access_expires_at > now());
CREATE POLICY private_constraints ON whereto.plan_constraints TO whereto_plan_runtime
  USING (EXISTS (SELECT 1 FROM whereto.plans p WHERE p.id = plan_id))
  WITH CHECK (EXISTS (SELECT 1 FROM whereto.plans p WHERE p.id = plan_id));
CREATE POLICY private_itineraries ON whereto.generated_itineraries TO whereto_plan_runtime
  USING (EXISTS (SELECT 1 FROM whereto.plans p WHERE p.id = plan_id))
  WITH CHECK (EXISTS (SELECT 1 FROM whereto.plans p WHERE p.id = plan_id));
CREATE POLICY private_stops ON whereto.itinerary_stops TO whereto_plan_runtime
  USING (EXISTS (SELECT 1 FROM whereto.generated_itineraries i WHERE i.id = itinerary_id))
  WITH CHECK (EXISTS (SELECT 1 FROM whereto.generated_itineraries i WHERE i.id = itinerary_id));
CREATE POLICY private_sources ON whereto.source_metadata TO whereto_plan_runtime
  USING (EXISTS (SELECT 1 FROM whereto.itinerary_stops s WHERE s.id = stop_id))
  WITH CHECK (EXISTS (SELECT 1 FROM whereto.itinerary_stops s WHERE s.id = stop_id));
