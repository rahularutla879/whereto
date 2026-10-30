# Task 48 — initial PostgreSQL schema

Task scope: database foundation only. No save/retrieve endpoints, accounts, runtime database connection, public grants or complex-journey planner. Ordinary mock startup remains database-independent. See [database setup](database-setup.md) for the confirmed development project, ignored configuration and verified TLS.

## Tables and relationships

All application objects live in the private `whereto` schema, outside `public` and the Data API surface.

| Table | Purpose and important columns |
| --- | --- |
| `plans` | UUID identity; optional original **user-authored** text (1–4,000 characters); `data_mode` mock/real; payload `model_version`; timezone-aware creation/update timestamps. No account or contact fields. |
| `plan_constraints` | One row per plan (`plan_id` PK/FK): exact date, optional IANA timezone, user destination text, ordered/repeated activity IDs and grounded activity intents; single-day minute window and explicit-time flags; mode; first/between Strict/Flexible minutes/miles values and exclusivity; legacy first/per-leg/inter-stop caps; geography, accessibility, availability, dinner and revisit requirements. |
| `generated_itineraries` | Many options per plan: UUID, stable candidate hash ID, zero-based `option_position`, feasibility, travel classification, optional score, generation timestamp/version. No provider-generated title, explanation or aggregate travel snapshot. |
| `itinerary_stops` | UUID identity independent of order; itinerary FK; zero-based position/activity; nullable start/end/duration with explicit user/fictional/unknown timing basis. Provider venue identity and route provenance are child references, not cached venue facts. |
| `source_metadata` | Stop FK, provider-neutral slug, reference kind (`venue`, `incoming_route`, `first_leg`), permitted external ID, optional receipt timestamp, evidence status and fixed `identifier_only` storage policy. No provider content/URLs/coordinates/raw JSON. |
| `schema_migrations` | Administrative ledger: filename PK, SHA-256 checksum, application timestamp. Not a sixth product entity. |

`plans → plan_constraints` is one-to-zero-or-one structurally; Task 49 must atomically create the required constraints alongside a saved plan. `plans → generated_itineraries → itinerary_stops → source_metadata` are one-to-many. Deleting a plan cascades through its owned children; deleting an itinerary/stop removes its owned descendants. No global venue cache or orphaned source registry exists. Repeated visits and repeated activity categories remain representable.

Six PKs, four cascading FKs, four additional uniqueness constraints. Option position and candidate identity are each unique **within a plan**. Stop position is unique **within an itinerary**. A stop has at most one reference of each kind per provider. These unique indexes also index every child FK; no redundant FK-only indexes. `plans(created_at DESC,id)` supports future recent-plan listing; partial `source_metadata(provider,external_id)` supports identity lookup. No arbitrary four-stop/three-option database cap: current Pydantic limits still apply at the application boundary.

Checks reject negative positions, impossible minute windows, mismatched complete stop durations, invalid score ranges including NaN/infinity, incomplete travel preferences, unsupported modes/units, >200-mile limits, empty activity arrays, null activity elements, invalid region codes, out-of-range dinner indexes and invalid retention policies. PostgreSQL arrays preserve activity order and duplicates; JSONB is used only for the current grounded activity-intent map, not a whole request/response blob.

## Mapping to actual application contracts

Inspected `backend/main.py`, `models.py`, `real_planning.py`, `interpretation.py`, `location_policy.py`, `location_context.py`, `venue_models.py`, `routes.py`, `evidence.py`, `option_sessions.py`, `venue_details.py`, `database_check.py`; frontend `lib/planner.ts`, request/proxy contracts and `lib/planning-session.ts` before design.

- `PlanningRequest`/`PlannerInput` → plan constraints: `date`, `calendarTimezone`, `location`, `activities`, `activityIntents`, `startTime/endTime`, `explicitStart/End`, `transport`, `planningMode`, `firstTravel/betweenTravel` (`value/unit/mode/exclusive`), `maxFirstLegTravel`, `maxLegTravel`, `travel` (inter-stop only), their exclusivity flags, `geography`, `requireWheelchairAccess`, `requireAvailability`, `allowRevisits`, `dinner/dinnerStops`. Field names become snake_case. Preserve preferred Flexible values; the existing 2× maximum is computed, not stored a second time.
- `InterpretationInput.text` → optional `plans.original_request`. Saving free text needs deliberate minimization/redaction in Task 49: it may contain a home address or other sensitive information. `FirstTravel.originText` and `DestinationContext` provider/coordinate enrichment are deliberately omitted. `location_text` must come from the user's destination intent, not a copied Google formatted address.
- `RankedItinerary.candidate.id`, selection order, `feasibility`, `travelClassification`, optional `score` → generated option. `generated_at`, `generator_version`, `model_version` are persistence metadata, not claims that the current response supplies version information. Keep provider-derived ranking scores null for real plans pending retention review; position preserves selection order.
- `RankedItinerary.stops` / `PlannedStop` / frontend `Plan.stops` → ordered stops. Fictional or explicitly user-authored times/durations can be stored. Real unknown times remain null; do not copy provider-derived schedules into these columns. These columns do not implement explicit appointment/duration interpretation.
- `VenueFacts.provider/id`, `Venue.providerPlaceId`, `Source.provider/place_id`, mock fixture ID → venue source reference. Current `RouteLeg.provider` and evidence receipt/status → incoming-route/first-leg **provenance only**, not distance/time/evidence payload. The first route belongs to stop zero; later incoming routes belong to their destination stop by writer convention.
- `VenueFacts` names, addresses, coordinates, types, ratings, hours, URLs, credits and `RouteLeg` metrics are transient and excluded. Current display labels, descriptions, totals and feasibility explanations can embed provider facts, so entire `RankingResult`/frontend `Plan` snapshots are prohibited.
- `people`, `budget`, `groupBudget`, numeric cost controls and ranking preference `cost` are legacy contracts, not restored database requirements. No group size or numeric-budget column is introduced. A future explicitly supported financial feature requires a migration and policy review.
- `optionsToken`, `detailsToken`, `referenceToken`, continuation locks/budgets/frontiers, `recentSurpriseIds`, `startingLocation`, device/manual coordinates, search radius and pending clarification remain transient. A saved-plan ID is not a continuation capability or ownership proof.

## Migration approach and exact commands

Use existing pinned Psycopg 3, explicit numbered SQL, a checksum ledger and one transaction protected by an advisory transaction lock. No ORM, Supabase CLI, new driver or database reset. The initial file is `backend/migrations/0001_initial_planning.sql`.

From `/Users/rahularutla/Documents/whereto`, run **one** action at a time:

```sh
(
  set +x
  set -a
  source backend/.env.database
  set +a
  backend/.venv/bin/python -m backend.database_migrate check
)
```

`check` applies pending SQL and verifies it, then **rolls back**. It works on a fresh project and never commits. After SQL/diff/test review, replace the last line inside that subshell with `backend/.venv/bin/python -m backend.database_migrate apply`; it commits migration SQL and ledger together. Then run that subshell with `backend/.venv/bin/python -m backend.database_migrate verify` for a new **read-only** transaction checking tables, ledger/checksums, ownership, RLS, policies and grants. Repeating `apply` is a checked no-op. Editing an applied file, an unknown version, noncontiguous history or an existing untracked `whereto` schema fails closed. Do not manually paste this SQL repeatedly or modify the ledger to force success.

Migration filenames must have unique four-digit prefixes and lowercase names. Future changes add a new numbered file; never edit an applied migration. No rollback/reset/drop CLI exists. Destructive future migrations require owner approval. `apply` commits only after verification; an error rolls back pending work and prints a fixed message without raw database exceptions. Connection timeout 10 seconds, local statement timeout 15 seconds, local lock timeout 5 seconds. The tools use session pooler/5432, the existing CA, `sslmode=verify-full` and require actual TLS; no global/session-persistent settings are changed.

Offline checks run with ordinary `npm run test:backend`. For real SQL fixtures, use the private subshell above with:

```sh
WHERETO_DB_SCHEMA_TESTS=1 backend/.venv/bin/python -m unittest backend.test_database_schema -v
```

Each hosted test opens an explicit transaction, applies missing schema inside it, creates only disposable fixture rows, tests valid/invalid SQL and rolls back even on assertion failure. On a fresh project this also rolls back the DDL. No artificial records remain. Full default tests skip hosted fixtures; mocked tests never replace hosted verification.

## Security and ownership

Migration objects belong to the connected administrative owner (`postgres` in this confirmed project). No new login, runtime credential or broad role grant is created. Revoke schema and table privileges from `PUBLIC`, `anon`, `authenticated`, `service_role`; set owner-specific future table/sequence defaults in this schema. Explicitly enable **and force** RLS on all six tables, with no access policies. RLS alone is insufficient: schema/table grants are separately checked, including effective role privileges. No functions, security-definer code, sequences or views are added. No Supabase system schema/defaults outside `whereto` are altered. Never add this schema to API exposure/publications.

Administrative owner/BYPASSRLS roles can still access data. The ignored Task 47 credentials are for migration/verification only, never FastAPI runtime, a browser or `NEXT_PUBLIC_*`. No auth-derived row ownership is claimed. Task 49 must define a bounded server-side save/reopen access contract and transaction writer; Task 50 must establish reviewed least-privilege runtime identity, authentication/authorization, write validation, abuse/CSRF protection where applicable and ownership policies before public use. Do not grant table access to generic API roles to make persistence work.

Keep Data API disabled. Client-to-pooler TLS is verified; pooler-internal transport is not independently inspected. Existing platform network/SSL-enforcement settings are unchanged; client verification does not claim database-wide rejection of non-TLS clients. Hosting, connection pooling, secret management and network access require review before deployment.

## Provider storage and attribution policy

Reviewed October 30, 2026 against official [Places policies](https://developers.google.com/maps/documentation/places/web-service/policies), [Routes policies](https://developers.google.com/maps/documentation/routes/policies), [Maps service-specific terms](https://cloud.google.com/maps-platform/terms/maps-service-terms), and [Supabase API security](https://supabase.com/docs/guides/api/securing-your-api). Google permits indefinite Place ID storage. Its 30-day latitude/longitude exceptions are not general permission to store all Places/Routes content. This initial schema uses **none** of those temporary-cache exceptions.

Persist only Google Place IDs and app-owned provenance (provider/kind/receipt/status). No Google names, addresses, coordinates, opening hours, ratings, photos, contacts, links, attribution payloads, route metrics, or derived textual snapshots. There is no expiring content cache requiring a cleanup scheduler or backup purge. Fresh display data must preserve required Google Maps/third-party attribution and applicable map/display restrictions; a stored provider slug or observed timestamp is not sufficient attribution and does not prove current availability. Task 49 must define explicit refresh/missing-provider behavior without silently calling Google or presenting stale snapshots. No live Google calls are authorized in Task 48.

Provider identity is neutral text; provenance-only rows may name other providers, including `local_identity`. For now only `google_places` and the project's fictional `mock` fixture may populate a venue external ID; a database check rejects IDs for unreviewed providers and all route references. Approving another provider's identifier/content retention requires a new migration and license/attribution review. Mock fixture IDs resolve against the existing fictional dataset; no venue snapshots are needed.

Free-text user input and intent fields are not provider-content escape hatches. SQL enforces structure, not semantic origin: Task 49 needs a strict allowlist mapper, Pydantic validation and tests that reject copied provider content, secrets/tokens and sensitive origins. Administrative users can always misuse authorized columns; this task adds no public writer. Supabase hosting does not grant third-party content rights: its [Acceptable Use Policy](https://supabase.com/aup) prohibits infringing content; the [Terms](https://supabase.com/terms) and [Data Processing Addendum](https://supabase.com/legal/customer-resources/data-processing-addendum) leave customer-data rights and appropriate processing obligations with the customer. [Free-plan backup guidance](https://supabase.com/docs/guides/platform/backups) recommends regular exports; this task creates no backup automation or paid backup feature. Future retention/deletion policy must cover any exports and backups as well as live rows. Applicable regional/account agreements, rights to derived ranking/feasibility values, future alternative-provider permissions and a user-request deletion/backup policy remain review points before broader persistence.

## Extension points and trade-offs

UUID stop identity and unbounded ordinal positions support later additive dependency/mandatory/named-destination columns. Nullable timing supports unknown duration; request timezone/window and explicit flags distinguish user deadlines from defaults. Separate first-leg and incoming-route references distinguish origin travel from inter-stop travel. Future 50A–50E migrations can introduce confirmed endpoint/return topology, dependency edges, total-journey constraints and richer permitted evidence. **No such logic or unsupported total-trip constraint is implemented here.** Current `inter_stop_minutes` must never be reinterpreted as a return-inclusive deadline.

Deliberately deferred: exact current response round trip, provider snapshots, durable sessions, globally reusable venue tables, account ownership, title/search indexes, arbitrary metadata blobs and schema-enforced gapless stop numbering. Task 49's writer must require one constraints row, complete contiguous stops starting at zero, correct route-to-stop associations and matching activities; SQL enforces uniqueness/nonnegative order and referential integrity, not cross-row plan completeness. `updated_at` defaults to creation time; Task 49 must set it on each edit within its transaction (no trigger needed before a writer exists). IANA zone validity and activity/dinner semantics remain in existing Pydantic validation.

## Actual hosted evidence

On October 30, 2026, rehearsal and rollback fixtures passed on the actual PostgreSQL engine; the migration was then applied to the confirmed development project. Separate read-only verification passed, repeated apply was a safe no-op, and the hosted catalog confirmed 6 PKs, 4 FKs, 4 additional unique constraints, 51 checks and 12 indexes. All five application tables are empty; the ledger has one checksummed row. Data API was independently confirmed off in the dashboard. Final hosted schema/migration tests passed 16/16 with rollback cleanup. See the final Task 48 checkpoint in HANDOVER.md for full regression, smoke and delivery evidence. **Task 48 is complete based on actual hosted verification.** Tasks 49, 50 and 50A–50E remain unstarted.
