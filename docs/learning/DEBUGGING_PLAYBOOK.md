# Debugging playbook

Start in `/Users/rahularutla/Documents/whereto`. Record current commit, safe visible message, endpoint, HTTP status and code/correlation ID if available. Keep private links, raw request bodies, origin coordinates, credentials, SQL connection strings and evaluation journal content out of shared reports. Do not resubmit a paid action repeatedly to gather evidence.

## A five-step diagnosis

1. Identify which operation failed: page load, interpretation, ordinary generation, advanced continuation, save/reopen or current-detail refresh.
2. Read the existing browser Network entry if retained. Distinguish HTTP failure from 200 with clarification/no_results. Inspect only the necessary safe fields.
3. Find the message/code in source with `rg -n`; follow its condition and caller.
4. Read the matching offline fixture/test and determine which service it replaces.
5. Apply a minimal justified fix only in a separately scoped change. This documentation task changes no application behavior.

## Frontend not loading

**Observe:** browser connection refusal, page error or build/runtime console error. **Read-only checks:** `pwd`, `git status --short`; if already running, request `/api/health` with the bounded health command. Inspect the frontend Terminal's first error. [scripts/dev-server.mjs](../../scripts/dev-server.mjs) manages process startup/ownership; [app/layout.tsx](../../app/layout.tsx), [app/page.tsx](../../app/page.tsx), [globals.css](../../app/globals.css) own rendering.

**Interpretation:** a dead port differs from a React exception. Don't delete `.next`, reinstall everything or change CSS as the first fix. Normal startup commands are in [DEVELOPMENT_COMMANDS.md](DEVELOPMENT_COMMANDS.md). Do not kill an unknown process that owns port 3000.

## Backend not running or proxy unavailable

**Observe:** FastAPI `/health` is unreachable or Next `/api/health` reports backend unavailable; generation may say `backend_unavailable`. **Check:** existing backend Terminal and server-side `BACKEND_URL` configuration name/default, not its private environment dump. [app/api/health/route.ts](../../app/api/health/route.ts) uses a three-second timeout and validates the health shape.

**Interpretation:** if direct health succeeds but proxy fails, investigate proxy destination/address/response validation. If import/startup reports the production activation refusal, do not remove `validate_environment`: the cloud prerequisites are intentionally absent. Restart only using the documented local launcher when appropriate; do not switch hosting flags to suppress it.

## AI inference slow or unavailable

**Observe:** `/api/interpret`, `llm_unavailable`, `llm_timeout`, `llm_invalid_response` or proxy `ai_unavailable`. **Read:** [AISettings](../../backend/ai/__init__.py), [OllamaProvider](../../backend/ai/ollama.py), [ai_readiness](../../backend/ai_readiness.py). If installed, `ollama list` is an inventory check; do not run generate/chat/smoke as documentation verification.

**Interpretation:** unavailable service/model, timeout and invalid structured output are different. Existing protected diagnostics can show local AI stage timing/readiness if already enabled; no new inference is needed to inspect a retained snapshot. A cold load or occupied inference slot is not proof a new prompt will fix latency. The single inference admission slot intentionally has no queue. Never bypass strict validation or silently enable a cloud fallback.

## No venues found

**Observe:** no_relevant_venues, empty activity pool, destination_unresolved or geographic_verification. **Read:** [real_planning.real_plans](../../backend/real_planning.py), [sequential_discovery](../../backend/sequential_discovery.py), [venue_quality](../../backend/venue_quality.py), [venue_geography](../../backend/venue_geography.py). Separate no relevant supply in checked results from discarded outside-area/ambiguous evidence.

**Recovery:** correct a destination/activity or deliberately request further finite discovery where the interface offers it. Don't substitute an activity or infer the destination from a private start. For Hitech/HITEC, inspect `test_hitec_geography.py` and the narrow parent-bound rule. The original incident's precise provider response was unavailable; an offline spelling reproduction is not recovered incident evidence. Mock Sydney/Hitech requests cannot become successful fictional Baltimore requests without changing the user's goal.

## Venues exist but no feasible itinerary

**Observe:** `insufficient_routing`, infeasible/insufficient_data errors, rejectionReasons, advanced no_results or unverified timing reasons. **Read:** [ranking.evaluate_candidate](../../backend/ranking.py), [feasibility](../../backend/feasibility.py), [advanced_routing](../../backend/advanced_routing.py), [advanced_timing](../../backend/advanced_timing.py).

**Check:** complete required occurrence count, dates, fixed-event/window conflict, each leg versus sum, strict/exclusive limits, real mode, route freshness and required identity. Unknown hours/dwell/price/session evidence is not known closure or known success. “No checked route fits” is not exhaustive proof. Further options/discovery require explicit actions and existing budgets; never auto-relax a limit or fabricate travel.

## Date or timezone clarification

**Observe:** question fields `date`/`time`, date issues, outing_date_expired or safe missing-date message. **Read:** [date_resolution](../../backend/date_resolution.py), [location_context](../../backend/location_context.py), [outing-date-field](../../components/outing-date-field.tsx), [backend/TESTING.md](../../backend/TESTING.md).

**Check:** source date wording, explicit manual correction, destination-calendar evidence, missing year and date expiry at publication. Browser timezone is not always destination timezone. A session may expire while a calendar date is still valid. For failing historical tests, use the declared scenario clock; do not weaken production expiry or keep moving dates. An ambiguous local daylight-saving clock boundary must not be guessed.

## Invalid starting point

**Observe:** confirm-start notice, invalid_origin, unverified_origin, changed_origin_request or starting lookup disabled. **Read:** [location-controls](../../components/location-controls.tsx), [starting_places](../../backend/starting_places.py), [starting_areas](../../backend/starting_areas.py), [surprise](../../backend/surprise.py).

**Check:** typed versus confirmed selection, source (`mock` cannot route real venues), explicit device permission, changed request context, lookup gate and allowed capability. A city/neighborhood approximate point is not a precise address. GPS failure can offer safe manual recovery. Do not trigger location permission on page load or borrow the destination as the origin.

## Return-to-origin conflict

**Observe:** “This journey must return to a confirmed starting point. Choose current location or a manual starting place.” **Read:** `prepareSurprise`, `generateOuting` requireOrigin, `AdvancedRouter._plan`.

**Recovery:** deliberately confirm a current/manual start. Surprise Me means beginning at a first activity without a private origin journey; it cannot silently satisfy an explicit return. “Home” is a separate unresolved endpoint unless the source/answer establishes the relationship. Whole-trip return duration includes travel back, not just inter-stop legs. Do not remove the requirement to obtain cards.

## Google Maps failures and pauses

**Observe:** provider_quota_rejected, provider_local_rate_limit, provider_local_admission, provider_service_error or a resumable continuation pause. **Read:** [provider_errors](../../backend/provider_errors.py), [failures](../../backend/failures.py), [provider_budget](../../backend/provider_budget.py), [development_cost](../../backend/development_cost.py), [routes_transport](../../backend/routes_transport.py).

**Check:** remote versus local refusal, search versus matrix stage, retained route freshness, finite allowance and existing sanitized diagnostics. Never print OAuth tokens/provider bodies. Rolling admission can return a pause; no background retry is implied. Refreshing does not reset shared usage. Corrupt ledger means stop and investigate; never delete it. Account budget alerts are not hard stops. No provider retry, quota/billing change or fresh paid verification is authorized by this playbook.

## Saved-plan or database errors

**Observe:** database_not_configured, database_runtime_role_required, database_connection_failed, database_authentication_failed, database_access_denied, save_transaction_failed, save_reference_expired or saved_link_unavailable. **Read:** [saved_plans](../../backend/saved_plans.py), [persistence_config](../../backend/persistence_config.py), [persistence-proxy](../../lib/persistence-proxy.ts), [database setup](../database-setup.md).

**Check:** correct restricted runtime profile rather than administrator config, TLS, receipt lifetime/membership and selected ID. Do not paste credentials or test the real database for a prose lesson. Save failure preserves cards; no success link means no claimed successful save. An unavailable link deliberately does not reveal whether a private row exists. Reopen may work while current Google refresh fails; routes are not stored as fresh evidence. Use the same selection for an explicitly approved retry rather than fabricate a new token.

## Test failures

**Observe:** failing test name, assertion or setup error. **Check:** expected calendar/route/monotonic clock, fixture environment, opt-in resource conditions, child-process cleanup and generated Next type timing. [backend/TESTING.md](../../backend/TESTING.md) explains isolated clocks. Build and typecheck should be sequential. A mocked HTTP test is not live Google acceptance; a compilation pass is not a behavioral pass.

Use a focused offline test after understanding it. Do not unskip hosted or lifecycle suites, stop owner ports, loosen assertions, enlarge timeouts, reset journals or change frozen outputs merely to make a run green. Report actual failures and environment blocks separately. No application suite was rerun for this handbook.

## Where logs exist, and what they cannot tell you

[failures.evidence](../../backend/failures.py) logs a reference, stable code/operation and exception type. It deliberately omits exception messages, SQL, provider bodies, raw requests and tokens. [operations](../../backend/operations.py) has fixed structured events and bounded aggregates; protected [development diagnostics](../../app/dev/diagnostics/page.tsx) shows declared local snapshots only when enabled. The launcher inherits Terminal output rather than guaranteeing a persisted application log file.

An older Network entry or terminal scrollback may no longer be available. Aggregates cannot reconstruct it. Say “original response unavailable; offline fixture reproduces X” rather than inventing a correlation ID, code or root cause. Do not add content logging or send a new paid request just to fill an evidentiary gap.

## Local V5.1 fixture

Use the [bounded fixture workflow](../task52-v51-local-application-integration.md). Unknown source requests cannot call a model. The original fresh-only helper refuses manual/pending overrides; use the later bridge below for current fixture compatibility. If a broad scenario run exhausts the normal shared allowance, isolate independent scenarios in separate test processes rather than reset a live session or raise limits.

## Edited V5.1 request or pending answer refuses

The [manual/pending bridge](../task52-v51-manual-pending.md) now supports issued snapshots and bounded manual controls. Check whether the textarea changed: old pending state must be cleared. A matching snapshot still needs fresh source proof. Check its reference, raw identity and original monotonic expiry; restart intentionally loses provenance. Activity/order changes require new source, not a date/location answer. Initial non-default spending/party/cost and unsupported source contexts remain blocked.

## Packaging startup refusal

Exit 78 from a packaging launcher means configuration/deployment dependencies require review; values are deliberately not echoed. Keep the backend production refusal intact. Check the [environment contract](../../deployment/environment-contract.md) and hosted blockers rather than adding an override. A green `/health` proves process reachability only. Test unavailable dependencies with loopback fakes, never paid inference or owner data. Docker absent means container verification is blocked; native tests are separate evidence.

## Local Docker context, tmpfs and shutdown

If Docker reports a missing default socket while Colima is running, select `DOCKER_CONTEXT=colima-whereto-task52` for the test command; the default context was deliberately preserved. If tmpfs receipt copying fails, the checked-in harness uses `docker exec` streams, not a host mount. Next SIGTERM exit 143 is intentional after cleanup in the installed framework; do not rewrite the launcher to force zero. SIGKILL 137, OOM or missing backend shutdown completion fails the test. A lost receipt after restart must remain rejected (409), not be reminted. Container success does not waive scanner findings or hosted startup refusal.
