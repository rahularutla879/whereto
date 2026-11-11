# Task 52B — V5.1 local application fixture

This report describes the `e720a45` checkpoint. The later [manual/pending bridge](task52-v51-manual-pending.md) supersedes its local manual-override limitation; original verification results remain historical.

Baseline: `8116465e8f3bc9c5cc69afc6c13d3c2914d1dbf7`. Integration identity: `52b-v51-local-application-fixture-v1`. This checkpoint adds a disposable test process, server-owned authored extractions and application-boundary tests. It changes no application startup, public DTO, ordering grammar, model prompt, dependency or production source file.

## Integration point

`scripts/task52_v51_application_fixture.py` installs the existing generalized `interpret_for_development` at `backend.main.interpret_request` only inside its explicit context. The existing `/api/interpret` handler still validates the public input, applies request admission, wraps interpretation disposition and creates the existing advanced session. The fixture does not accept a client extraction, graph, semantic receipt or entitlement. Supplied extractions come exclusively from `scripts/task52_v51_application_cases.json`; this lookup supplies fake model output, not gold-based graph repair. The generalized validator still proves each output against its actual source. Unknown sources safely fail without a model fallback.

The unchanged Next form → `generateOuting` → interpretation proxy → FastAPI → advanced token → `/api/plans/advanced` → resolution/router/timing → `PlanCard`/View Plan → save receipt selection → reopen interfaces are exercised. No second planner or normalizer was added. A compatible graph alone cannot mint a token: the existing complete disposition and session creation boundary remain in use. The foundational semantic-receipt registry is not newly activated.

## Isolation and controls

Normal `dev`, `start`, backend startup and production builds never import the fixture. There is no application flag or request parameter enabling V5.1. This local fixture assumes the operator does not republish it through a public reverse proxy; it is not a production service. The explicit fixture refuses production/hosted environment markers before setup and binds only `127.0.0.1`. Its middleware rejects non-loopback clients, hosts, origins and forwarding claims. `--legacy` selects the unchanged legacy interpreter with the same fake extraction; it never selects a live provider.

Existing Task 50E synthetic Places/matrix fixtures, scoped calendar helpers and production provider-budget/session controls are reused. External HTTP sends, outbound socket connections, the model factory and real PostgreSQL connection all raise before I/O. No keys are loaded by this fixture and the automated subprocess inherits only PATH and explicit test settings. No real provider fallback exists. Synthetic counters contain counts only, not source bodies, capabilities or coordinates. Every independent automated outing has its own backend process and normal fresh process-local allowance; a live session's allowance is never reset or enlarged to complete the matrix.

The save service still validates the opaque receipt, candidate set, selected ID and access-token binding. Only its database context and document read/write storage are replaced with an ephemeral, locked `MemoryDocuments` store. It validates the existing `SavedDocument` DTO and idempotent selection. Reopen returns only the selected itinerary and current timing remains unverified. This proves application serialization and receipt selection, not PostgreSQL transactions, RLS, durable expiry or multi-instance behavior. Those remain covered by existing persistence/security regressions. Restarting this fixture discards its synthetic sessions and saved documents. No persistent user data or real journal can be written.

## Scenarios and interpretation limits

The server-owned corpus has the original five approved requests, seven independent requests and one ordinary legacy request. Nine supported sources produce advanced options after explicit missing-context answers. Contradictory pharmacy/bank instructions, unsupported `versus`, and a merged repeated-stop extraction clarify before venue/routing work. Tests check source occurrence order, independent required coffee, named college, return ending, inclusive 180-minute limit, optionality, selected save/reopen and rejected client authority fields.

Independent examples include three-stop `then`, a four-stop list, optional beginning and middle stops, bounded `aur`, unsupported language and ambiguous repeated occurrences. The original groceries case supplies an optional final stop. Existing generalized tests separately cover flexible permutations and closure when optional stops are skipped. New ASGI tests exercise unreachable optional-stop omission, unreachable required routes and whole-trip timing through the actual API middleware/endpoints. Exact user-provided visit lengths can make the bound feasible; an overrun removes options.

The inherited development adapter accepts fresh source extractions only. Initial manual interpretation overrides or legacy pending snapshots are deliberately blocked with existing rephrase clarification. Supply missing date/destination through the existing advanced follow-up controls after initial validation. For browser date text entry, commit the value by leaving the field before submitting, then answer the destination question. Do not edit unrelated fields before the requested follow-up. This is not general production manual/pending integration.

Unknown hours and visit lengths are not fabricated. Some cards are provisional: verified synthetic route feasibility is distinct from confirmed real opening hours or complete visit schedules. In particular, a whole-trip bound remains visibly unverified until visit-duration evidence is provided. Active included-stop cards do not currently badge optional attendance; the saved view retains and shows the typed required/optional metadata. That existing presentation limitation was not changed here. Existing card labels say “Real venues” because the unchanged provider-shaped path is used; every venue in this workflow is explicitly Synthetic and no live availability is established. Do not share fixture output as verified recommendations or follow its Maps links.

## Local use

From the repository root, in separate terminals:

```sh
PYTHONPATH=. backend/.venv/bin/python -m scripts.task52_v51_application_fixture --port 8027
BACKEND_URL=http://127.0.0.1:8027 node node_modules/next/dist/bin/next dev --hostname 127.0.0.1 --port 3027
```

Open `http://127.0.0.1:3027` only against that fixture. Do not use the normal backend on port 8000 for these checks. Stop both task processes afterward. A locally served unchanged compiled build was also browser-tested; that does not add this mechanism to a production build.

Automated checks:

```sh
backend/.venv/bin/python -m unittest backend.test_v51_application_fixture backend.test_v51_ordering_preservation -v
node --import tsx --test lib/v51-application.test.ts
npm test
```

## Browser evidence and acceptance

Actual browser checks used the existing frontend on port 3027 and disposable backend on 8027. They exercised groceries/optional coffee, existing starting-method and date/destination controls, View Plan, choosing the second itinerary, Save Plan and private-link reopening with one selected itinerary; contradictory source clarification; and independent optional-middle ordering on mobile. Desktop width 1280 and mobile width 390 had matching document widths, with no horizontal overflow observed. Automated adapter tests cover the larger scenario matrix; they are not claimed as individual browser runs. No Maps links were opened.

Final checks: 1,395 distinct backend passes, 37 existing opt-in skips, zero failures/errors and 34 incomplete historical simulations out of 1,466 discovered methods. Counts are deduplicated across bounded partitions and focused runs, not presented as one uninterrupted full-suite pass. Of the exact previous 123 unfinished simulations, 89 completed without failures in three rounds of three four-minute workers; 34 were interrupted or not reached within those bounds. Standard discovery was separately partitioned/prioritized with custom suite wrappers retained, followed by a two-minute pass completing all remaining 139 non-historical IDs. No skip or historical test implementation changed. All 287 frontend tests passed; the finalized two application-boundary tests and seven fixture/API tests also passed. Ordering/source/replay coverage passed 83 tests; the broader initial focused backend run passed 222 with 16 existing skips. TypeScript, lint and production build passed. Configured-value and boundary-aware generic secret scans found zero matches; complete diff and handbook references reviewed.

See [machine-readable verification](task52-v51-local-application-verification.json) for exact checks, incomplete historical IDs and immutable-state hashes. The full backend suite is not claimed green unless every normally enabled test is completed. Historical paid classifications, prompts, Q1 rubrics, evaluator identities and diagnostic loss evidence remain unchanged.

## Remaining activation blockers

Independent semantic review, a separately approved production trust boundary, initial manual/pending compatibility, optional-stop presentation review and broader route/calendar qualification remain separate work. This checkpoint grants no paid evaluation, planning admission transport or production V5.1 activation. No further grammar or evaluation framework change was made. Task 53 remains unstarted.
