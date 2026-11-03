# Task 50E — local advanced outings

Current November 3 acceptance repair: [causes, unified UI, incremental exploration, bounds and verification](task50e-repair.md). This supersedes the original one-page limitation below.

Task 50E connects the existing interpreter, resolver, directed router and temporal
evaluator to the website and anonymous private links. Task 51 is not started.
This is an approved local-development integration; fresh clones/CI stay mock and
public production cannot enable real planning. Verification totals are recorded in
HANDOVER.md after the final checks.

## Flow and authority

The normal textarea makes one existing `/api/interpret` call. Simple outings keep
the ordinary planner. With all local gates enabled, a validated advanced request
gets a random 256-bit `advancedToken`. It references a server-owned `Session`;
no client interpretation, Place ID, route or feasibility verdict is authoritative.
The interpretation's original source text, Journey and effective calendar/mode/
travel/geography context stay in that session. There are at most 50 sessions, a
fixed ten-minute expiry and a nonblocking per-session work lock. No evidence goes
to localStorage or disk. The browser stores only the existing saved capability.

`POST /api/plans/advanced` accepts the token, an explicitly authorized starting
point, initial first/between preferences, or one bounded answer: a scoped named
choice, occurrence-indexed dwell duration, destination, ISO/natural date or HH:MM departure, or an explicit bounded continuation action.
It rejects unknown fields. Both proxies use the existing local-origin, 4096-byte,
no-store boundary; backend disconnect cancellation and provider admission remain.
Changing routing inputs after dispatch requires regeneration. The website retains
the validated extraction for preference edits, avoiding another Qwen call, and
reapplies accepted place/nearby/dwell/departure answers. Edited text clears that continuation.
New routing computations do not reuse evidence across changed modes or geography.

The session uses one `OutingBudget` for `StopResolver`, `AdvancedRouter` and all
bounded discovery/routing. Task 50B resolves required exact identities, activities,
brands and containment using the existing adapters. Actual candidate choices show
names/addresses/credits; selecting one must match the same unresolved server group.
It does no new search or AI extraction. Required unresolved stops remain required.
Expired/replayed/fabricated contexts cannot authorize arbitrary provider identities.

Task 50C retains required/optional occurrences, source/fixed/partial/flexible order,
verified endpoints and directional evidence. It admits whole paths within 27
pairs, four stops and existing stricter shared limits. It publishes at most three options per page from a retained bounded pool. The return leg is separate from the final named-destination leg.
Task 50D evaluates those trusted snapshots locally. A missing-duration answer only
amends an unspecified occurrence on a copy; an explicit original duration cannot
be overwritten through the answer API. Approximate answers remain unbounded for
hard feasibility. Exact, minimum, maximum and exclusive-under answers retain their
meaning. Departure answers use the existing clock parser and destination timezone;
no 10 AM default, browser-zone substitution, new geocoder or Matrix repeat is added.
Past or DST-ambiguous destination-local departures need correction before provider
work; an explicit departure in the original request is corrected by editing it.

The response contains minimized typed public stops, safe establishment Maps links,
actual order, optional omissions, directional legs, known travel, elapsed bounds,
applicable duration/deadline verdicts, hours evidence and specific uncertainty.
It excludes private origin coordinates/Place IDs/labels, home answers and raw
provider responses. A token appears only in the dedicated continuation field, not
in card metadata, stage diagnostics or logs. Public venue facts are transient.

## Results and supported limits

Proven infeasible options are removed. Fully supported timing sorts before
unverified timing without changing ordinary ranking weights. Unverified options
say so prominently. Known route-only travel stays separate from the elapsed
lower/upper range and user-supplied dwell. Hours are shown using existing evidence;
unknown hours never become an opening claim or reservation. Details include the
return/final leg and Maps directions only between public establishment identities.
Private-origin legs have no public direction URL containing precise coordinates.

The existing card styles, selection control and secure new-tab actions are reused.
Advanced exploration now supports explicit additional combinations, bounded same-area
discovery and scoped travel exceptions through its own trusted session. It reuses
the ordinary history/actions UI; it does not call ordinary server continuation handlers.
Pages have at most three options, with 24-path/27-pair computations, at most 32
explicit continuation actions/256 checked assignments and the original shared
provider budgets/expiry. See the repair report for exact bounds and blockers.

Return to a confirmed starting point is supported. Home still needs explicit
return-to-start confirmation; GPS never means home. Separate home addresses,
unverified/generic final endpoints and unsupported clock/timezone grammar remain
unresolved. Named final establishments use Task 50B identity evidence. Independent
mandatory spending, accessibility, dietary, ticket or reservation requirements
that this advanced contract cannot verify are blocked before discovery, with an
explicit edit explanation. No hard requirement is silently ignored. Same-mall
relationships require the existing verified containment evidence.

## Saving, reopening and compatibility

`SavedDocument` now accepts versions 1 and 2. Version 1 remains the ordinary format.
Version 2 uses the same five tables, restricted runtime identity, verified TLS,
forced RLS, hashed capability, transaction/advisory lock and 30-day expiry. No
migration, role/grant change, destructive rewrite or administrator runtime is added.
The existing positive `plans.model_version` and JSON preferences columns already
support this extension. Version 2 stores `advancedVersion`/`advancedOptions` in
app-owned preferences and `model_version=2` on newly saved plans.

A server receipt binds the exact selection and access token. Advanced saving keeps
only the selected option. The representation retains redacted source user text,
canonical Journey (including dwell, total/deadline, precedence and optionality),
actual source-occurrence order/omissions, ending role, explicit departure and exempt
Google Place IDs. Explicit private origin/home wording is redacted recursively.
Neither private origin points nor supplied separate-home answers are stored.
Google-derived venue names, addresses, coordinates, ratings, hours, route metrics,
full responses, attribution payloads or observed schedules are excluded. A historical
app timing verdict has explicit provenance and is never displayed as current proof.

Reopening reads committed SQL through capability/RLS and renders only the saved
selection. It does not reconstruct discarded routes. Original user stop phrases
remain recognizable when current details are unavailable; current approved selected
Pro refresh, manual hours and optional contacts retain their independent gates,
per-action replay protection and budgets. A separate named endpoint retains its
Place ID and Maps reference; it is not added to the four-stop automatic Details
allowance. No fifth paid enrichment is introduced. Saved links survive backend
restart; unsaved process-local sessions/receipts do not. Legacy owner records remain
readable and are inspected only read-only by the existing hosted compatibility test.

## Local startup

Working folder: `/Users/rahularutla/Documents/whereto`.

The owner-only ignored `backend/.env.development` may contain
`WHERETO_ADVANCED_DEV=1` and `WHERETO_STOP_RESOLUTION_DEV=1` alongside the already
approved real-mode configuration. The launcher allowlist accepts these two flags.
Restart the backend after changing its private profile. Normal commands remain:

```sh
npm run dev:backend
# In a second Terminal, from the same folder:
npm run dev
```

No flag belongs in browser code or a fresh-clone public environment. No Cloud quota,
billing/IAM/credential, model/context/memory or startup/shutdown changes are needed.

## Verification and performance

Tests use invented Google-shaped transports and refuse real HTTP sends. The new
integration suite covers scoped choices, exact destinations, required/optional
coverage, precedence, returns/final endpoints, modes/Strict limits, exact versus
approximate timing answers, expiry, duplicate computations, config changes,
receipt selection and token substitution. Existing 50A–50D suites cover their
broader semantic/order/mall/hours/DST/boundary matrix. Cross-language frontend tests
render actual server projections and saved version 2 documents. Unsupported cases
are asserted as blocked, not counted as successful generated itineraries.

Hosted checks perform a committed disposable version 2 write using the restricted
identity, reopen it from a separate Python process, test capability isolation and
delete only its exact generated hash with a committed absence check. Existing
hosted RLS/rollback/concurrency/legacy checks run separately. Browser checks use
isolated 3050/8050 fixtures, selected new-tab reopening/restart, desktop/mobile,
structured date/area/dwell answers, mode changes and ordinary regressions. They
establish application behavior, not live Google coverage or a full accessibility
audit. Final measured evidence and cleanup are in HANDOVER.md.

One college→coffee fixture: two searches plus one Matrix cell. At the existing
application estimates this is $0.069 Pro / $0.075 Enterprise gross. A two-stop
round trip uses three cells: $0.079 / $0.085. A separately requested existing
starting-place lookup adds $0.032 Pro. These reuse prior documented price
assumptions, not newly verified prices or posted billing. Clarification and timing
reevaluation add zero Google calls/cost; route edits require fresh bounded work.
Actual Google calls/charges throughout automated/browser checks: zero/$0.

A 20-run full fixture pipeline measured median 2.272ms / max 5.128ms, excluding
Qwen and real network. Stage medians: resolution 1.036ms, routing 0.456ms, timing
0.522ms. Fixed ordinary interpreter/validation fixtures (100 per revision) measured
0.383ms median before / 0.376ms after. These are local overhead observations, not
controlled CPU/network benchmarks or a speed guarantee. Four actual installed
Qwen checks passed: ordinary 12.917s then 7.069s; advanced 14.083s then 12.847s.
No model setting changed; no controlled cold/unload comparison was made.


Final acceptance (November 2): backend865 reported/830 passed/35 opt-in skips;
frontend245/245; focused180 reported/179 passed/one hosted skip; hosted suite57/57
plus final committed advanced repeat1/1; PTY lifecycle8/8. Final browser departure
entry uses explicit HH:MM text with a 24-hour destination-local hint. Typecheck,
lint, build, dependency consistency, production audit, configured-secret and full
Git diff checks pass. Browser synthetic dispatch totals are18 Enterprise searches,
2 Pro origin lookups,109 Matrix cells and6 Details actions ($1.359 existing gross
estimate); actual Google cost is$0. Temporary records/servers/tabs were cleaned,
normal3000/8000 servers restored and the ignored authorized owner profile enables
the two advanced switches. See HANDOVER.md for failures corrected before final
passes, actual browser scope and remaining limits.


## Task 50E follow-up: presentation, nearby origins and coverage

The follow-up repair removes repeated advanced card diagnostics, labels dwell answers
in minutes with explicit exact/bounded/approximate meaning, distinguishes nearby
consent from route origin and real expiry, preserves destination-local clocks,
clarifies traffic-unaware estimates and balances bounded discovery/routing across
all stop occurrences. Numeric development stage/coverage diagnostics remain private.
[Causes, measurements, safeguards and acceptance evidence](task50e-followup.md).
Task 51 remains unstarted.
