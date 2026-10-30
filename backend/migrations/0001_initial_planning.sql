-- Run only through backend.database_migrate (atomic/checksummed/locked).
-- No application content from Google is stored; only exempt Place IDs.
CREATE SCHEMA whereto AUTHORIZATION CURRENT_USER;
REVOKE ALL ON SCHEMA whereto FROM PUBLIC, anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA whereto REVOKE ALL ON TABLES FROM PUBLIC, anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA whereto REVOKE ALL ON SEQUENCES FROM PUBLIC, anon, authenticated, service_role;

CREATE TABLE whereto.schema_migrations (
    version text PRIMARY KEY,
    checksum text NOT NULL CHECK (checksum ~ '^[0-9a-f]{64}$'),
    applied_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE whereto.plans (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    original_request text CHECK (length(btrim(original_request)) BETWEEN 1 AND 4000),
    data_mode text NOT NULL CHECK (data_mode IN ('mock', 'real')),
    model_version integer NOT NULL DEFAULT 1 CHECK (model_version > 0),
    CHECK (updated_at >= created_at)
);
CREATE INDEX plans_created_at_idx ON whereto.plans (created_at DESC, id);

CREATE TABLE whereto.plan_constraints (
    plan_id uuid PRIMARY KEY REFERENCES whereto.plans(id) ON DELETE CASCADE,
    outing_date date NOT NULL,
    calendar_timezone text CHECK (length(btrim(calendar_timezone)) BETWEEN 1 AND 100),
    location_text text NOT NULL CHECK (length(btrim(location_text)) > 0),
    activities text[] NOT NULL CHECK (cardinality(activities) > 0 AND array_ndims(activities) = 1
        AND array_position(activities, NULL) IS NULL AND NOT ('' = ANY(activities))),
    activity_intents jsonb NOT NULL DEFAULT '{}' CHECK (jsonb_typeof(activity_intents) = 'object'),
    start_minute smallint NOT NULL DEFAULT 600 CHECK (start_minute BETWEEN 0 AND 1439),
    end_minute smallint NOT NULL DEFAULT 1440 CHECK (end_minute BETWEEN 1 AND 1440),
    explicit_start boolean,
    explicit_end boolean,
    transport text CHECK (transport IN ('walking', 'cycling', 'driving', 'transit')),
    planning_mode text NOT NULL DEFAULT 'origin' CHECK (planning_mode IN ('origin', 'surprise')),
    first_travel_value numeric CHECK (first_travel_value >= 0 AND first_travel_value <= 1440),
    first_travel_unit text CHECK (first_travel_unit IN ('minutes', 'miles')),
    first_travel_mode text CHECK (first_travel_mode IN ('strict', 'flexible')),
    first_travel_exclusive boolean NOT NULL DEFAULT false,
    between_travel_value numeric CHECK (between_travel_value >= 0 AND between_travel_value <= 1440),
    between_travel_unit text CHECK (between_travel_unit IN ('minutes', 'miles')),
    between_travel_mode text CHECK (between_travel_mode IN ('strict', 'flexible')),
    between_travel_exclusive boolean NOT NULL DEFAULT false,
    max_first_leg_minutes smallint CHECK (max_first_leg_minutes BETWEEN 0 AND 1440),
    max_first_leg_exclusive boolean NOT NULL DEFAULT false,
    max_leg_minutes smallint CHECK (max_leg_minutes BETWEEN 0 AND 1440),
    max_leg_exclusive boolean NOT NULL DEFAULT false,
    inter_stop_minutes smallint CHECK (inter_stop_minutes BETWEEN 0 AND 1440),
    inter_stop_exclusive boolean NOT NULL DEFAULT false,
    strict_destination boolean NOT NULL DEFAULT false,
    excluded_regions text[] NOT NULL DEFAULT '{}' CHECK (excluded_regions <@ ARRAY['VA','MD','DC']::text[]
        AND array_position(excluded_regions, NULL) IS NULL),
    require_wheelchair_access boolean NOT NULL DEFAULT false,
    require_availability boolean NOT NULL DEFAULT false,
    allow_revisits boolean NOT NULL DEFAULT false,
    dinner boolean NOT NULL DEFAULT false,
    dinner_stops integer[] CHECK (array_position(dinner_stops, NULL) IS NULL
        AND 0 <= ALL(dinner_stops) AND cardinality(activities) > ALL(dinner_stops)),
    CHECK (end_minute > start_minute),
    CHECK ((first_travel_value IS NULL AND first_travel_unit IS NULL AND first_travel_mode IS NULL AND NOT first_travel_exclusive)
        OR (first_travel_value IS NOT NULL AND first_travel_unit IS NOT NULL AND first_travel_mode IS NOT NULL)),
    CHECK (first_travel_unit <> 'miles' OR first_travel_value <= 200),
    CHECK ((between_travel_value IS NULL AND between_travel_unit IS NULL AND between_travel_mode IS NULL AND NOT between_travel_exclusive)
        OR (between_travel_value IS NOT NULL AND between_travel_unit IS NOT NULL AND between_travel_mode IS NOT NULL)),
    CHECK (between_travel_unit <> 'miles' OR between_travel_value <= 200)
);

CREATE TABLE whereto.generated_itineraries (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id uuid NOT NULL REFERENCES whereto.plans(id) ON DELETE CASCADE,
    option_position integer NOT NULL CHECK (option_position >= 0),
    candidate_id text NOT NULL CHECK (length(btrim(candidate_id)) BETWEEN 1 AND 200),
    feasibility text NOT NULL CHECK (feasibility IN ('confirmed', 'provisional', 'violated')),
    travel_classification text NOT NULL DEFAULT 'unverified'
        CHECK (travel_classification IN ('matching', 'outside_preference', 'beyond_limit', 'unverified')),
    ranking_score double precision CHECK (ranking_score BETWEEN 0 AND 1),
    generated_at timestamptz NOT NULL DEFAULT now(),
    generator_version text CHECK (length(btrim(generator_version)) BETWEEN 1 AND 100),
    UNIQUE (plan_id, option_position),
    UNIQUE (plan_id, candidate_id)
);

CREATE TABLE whereto.itinerary_stops (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    itinerary_id uuid NOT NULL REFERENCES whereto.generated_itineraries(id) ON DELETE CASCADE,
    position integer NOT NULL CHECK (position >= 0),
    activity text NOT NULL CHECK (length(btrim(activity)) BETWEEN 1 AND 107),
    -- Only user-authored or fictional schedule values, never cached Google data.
    timing_basis text NOT NULL DEFAULT 'unknown' CHECK (timing_basis IN ('unknown', 'user', 'fictional')),
    start_minute smallint CHECK (start_minute BETWEEN 0 AND 1439),
    end_minute smallint CHECK (end_minute BETWEEN 1 AND 1440),
    duration_minutes smallint CHECK (duration_minutes BETWEEN 1 AND 1440),
    CHECK (end_minute IS NULL OR start_minute IS NULL OR end_minute > start_minute),
    CHECK (start_minute IS NULL OR end_minute IS NULL OR duration_minutes IS NULL
        OR end_minute - start_minute = duration_minutes),
    CHECK (timing_basis <> 'unknown' OR (start_minute IS NULL AND end_minute IS NULL AND duration_minutes IS NULL)),
    UNIQUE (itinerary_id, position)
);

CREATE TABLE whereto.source_metadata (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    stop_id uuid NOT NULL REFERENCES whereto.itinerary_stops(id) ON DELETE CASCADE,
    reference_kind text NOT NULL CHECK (reference_kind IN ('venue', 'incoming_route', 'first_leg')),
    provider text NOT NULL CHECK (provider ~ '^[a-z][a-z0-9_]{0,63}$'),
    external_id text CHECK (length(btrim(external_id)) BETWEEN 1 AND 200),
    observed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    evidence_status text NOT NULL DEFAULT 'unknown'
        CHECK (evidence_status IN ('unknown', 'reported', 'estimated', 'fictional', 'unverified')),
    storage_policy text NOT NULL DEFAULT 'identifier_only' CHECK (storage_policy = 'identifier_only'),
    -- Unknown providers can record provenance, but identifiers need license review.
    CHECK (external_id IS NULL OR (reference_kind = 'venue' AND provider IN ('google_places', 'mock'))),
    CHECK (provider <> 'google_places' OR (reference_kind = 'venue' AND external_id IS NOT NULL
        AND external_id ~ '^[A-Za-z0-9_-]+$')),
    UNIQUE (stop_id, reference_kind, provider)
);
CREATE INDEX source_metadata_lookup_idx ON whereto.source_metadata (provider, external_id) WHERE external_id IS NOT NULL;

-- Explicit protection even when platform defaults change. Owners/BYPASSRLS
-- administrative credentials remain privileged; these are not runtime credentials.
ALTER TABLE whereto.schema_migrations ENABLE ROW LEVEL SECURITY;
ALTER TABLE whereto.schema_migrations FORCE ROW LEVEL SECURITY;
ALTER TABLE whereto.plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE whereto.plans FORCE ROW LEVEL SECURITY;
ALTER TABLE whereto.plan_constraints ENABLE ROW LEVEL SECURITY;
ALTER TABLE whereto.plan_constraints FORCE ROW LEVEL SECURITY;
ALTER TABLE whereto.generated_itineraries ENABLE ROW LEVEL SECURITY;
ALTER TABLE whereto.generated_itineraries FORCE ROW LEVEL SECURITY;
ALTER TABLE whereto.itinerary_stops ENABLE ROW LEVEL SECURITY;
ALTER TABLE whereto.itinerary_stops FORCE ROW LEVEL SECURITY;
ALTER TABLE whereto.source_metadata ENABLE ROW LEVEL SECURITY;
ALTER TABLE whereto.source_metadata FORCE ROW LEVEL SECURITY;
REVOKE ALL ON ALL TABLES IN SCHEMA whereto FROM PUBLIC, anon, authenticated, service_role;
