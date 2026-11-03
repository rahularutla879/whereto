# Task 50E acceptance repair — November 3, 2026

This repairs the owner's eight acceptance issues against `0fd28e0`. Task 51
remains unstarted. All Google results used for verification are invented and
actual Google transport is blocked. This is still the approved local MVP.

## Causes and corrections

| Reported issue | Reproduced cause | Repair |
| --- | --- | --- |
| College + coffee asks for tomorrow again | 50E forced an explicit date whenever the initial destination timezone was unknown, before resolving the mandatory college. | Resolve the required named identity once first; use its verified public address/timezone evidence, then resolve the original relative date. Unknown evidence still needs clarification. |
| Extra search-area question | The advanced session required a destination string and did not offer deliberate reuse of the confirmed origin. It correctly kept origin and destination separate, but had no integrated continuation. | Use the existing Location preference; offer explicit nearby consent. A prior approved origin lookup can supply transient verified calendar evidence, while GPS coordinates alone cannot invent a timezone. |
| Cramped follow-up and date error | Advanced answers used separate unstyled forms below results, with text date entry and a strict ISO-only input contract. | All questions are inside the original planning form. Location and Date use canonical preference state; native ISO dates and supported natural date answers use the existing deterministic parser. Dwell, departure, choices and home confirmation use the same spacing and controls. |
| Dinner/bowling rejected | Actual Qwen added a redundant forward edge to an unordered source list. The 50A validator demanded an explicit ordering word and returned its generic conflict message. | Remove only source-grounded forward edges that merely restate the default source order when no explicit order cue exists. Do not bypass validation or normalize reversed, cyclic or conflicting intent. |
| Grocery/ATM/45-minute trip rejected | Actual Qwen produced the same redundant forward edge. Its ATM five-minute dwell, return and inclusive 45-minute maximum were correct. Another requested variant used a bare `return` endpoint that validation rejected. | Preserve all extracted constraints; normalize the redundant representation and accept a source-grounded bare return in the supported return/deadline grammar. Missing grocery dwell is a specific field question, not a semantic conflict. |
| Different advanced cards | 50E built a second card shell instead of adapting to the original component. | Extract the unchanged ordinary card shell into `PlanCard`; inject only advanced itinerary details and relevant warnings. Shared artwork, icons, headings, disclosures, readable dates, notices and responsive grid remain. |
| Extra Select itinerary click | The new button duplicated the established selected-itinerary save dropdown. | Remove it. The existing dropdown + Save Plan binds the chosen ID to the receipt; second-option selected-only reopening is tested. |
| No advanced exploration | 50E intentionally disabled ordinary alternative handlers and exposed one computed page. | Implement separate trusted incremental advanced actions, using the same interaction/history components and the original shared outing budget. |

The public six-request Qwen outputs are captured as test fixtures in
`backend/repair_extractions.json`. They are semantic examples, not provider data or
a production fallback. Six fresh installed-Qwen runs after repair retained every
expected requirement and passed interpretation/validation: college 16.424s;
grocery return 10.220s; grocery/ATM/45-minute return 15.019s; ordinary dinner/bowling
11.354s; dinner/drinks 6.831s; pharmacy/ATM/one-hour return 22.727s. These measurements
exclude Google and are not a controlled cold/warm or hardware comparison. No
prompt, schema, model, context, memory or warmup setting changed.

## Incremental authority and bounds

`/api/plans/advanced` retains its opaque server session and initial configuration.
It additionally accepts an explicit `action`: `different`, `discover` or `beyond`.
`includeBeyond` retains a deliberate travel exception while explicitly discovering
more; it does not waive any whole-trip duration, absolute deadline, hours or
reachability constraint. `searchNearOrigin` is a separate explicit geographic choice.
Responses expose `canExpand`, `canDiscover` and `canShowBeyond`; no client route,
venue verification or verdict is authoritative.

The resolver retains successful normalized candidates and opaque cursors only in
memory. Discovery adds at most two same-area pages/variants per action, at most
six pages per activity, retaining at most 100 candidates per group. Named mandatory
identities are never replaced or rediscovered merely to browse. All new candidates
pass existing relevance, deduplication, geography and containment requirements.
A failed dispatched page is consumed; a pre-dispatch local admission failure can
be resumed deliberately. Quota/attempt limits remain independent of search coverage.

The router keeps directional evidence and checked assignment signatures. Each
explicit computation retains the four-stop, 24-path beam and 27-pair union bound;
only missing pairs are dispatched. Already checked complete assignments are
excluded before beam truncation, so further retained combinations can be reached.
The session allows at most 32 explicit continuation actions and 256 checked paths,
within its original ten-minute expiry and shared provider budgets. Timing is
reevaluated locally for all retained candidates; a page contains at most three
eligible, previously unoffered itineraries. Proven whole-trip failures cannot be
published as compliant exceptions. Only scoped first/between travel limits can be
excepted; a violated original aggregate travel cap remains a blocker.

The existing Previous/Next component reads immutable memory snapshots with zero
provider/Qwen calls. Field answers amend their correct occurrence; route/mode
edits invalidate incompatible evidence and reuse the validated extraction. Old
pages survive failed continuation or expiry. Expired actions are disabled after
the safe rejection; regeneration remains available. No background queue, automatic
retry, new provider operation or quota increase is introduced.

## Product parity checklist

| Area | Ordinary and advanced behavior |
| --- | --- |
| Prompt, starting method, preferences | Same controls; explicit origin and destination remain separate. |
| Follow-ups | Inside the same main form; canonical Date/Location; no nested forms or results-area forms. |
| Dates | Native picker by default; optional words mode uses the same state/input and deterministic parser. Accepted answers normalize to ISO. |
| Cards | Same `PlanCard`, art/icon layout, typography, route row, View plan and source credits. |
| Details | Advanced-only return/final legs, known travel versus elapsed bounds, dwell/deadline and omissions live inside the shared disclosure. |
| Warnings | Concise per-option material warning; one shared Before you go block. Unknown hours never become availability. |
| Save/open | Existing dropdown + Save Plan and private new-tab actions; selected-only advanced document. |
| Alternatives | Same button layout and Previous/Next; advanced server work remains constraint-aware. |
| Failure/expiry | Safe explanations, retained input/pages, no silent relaxation or automatic retries. |

## Persistence, security and retention

No migration or new table is needed. Version 2 remains backward compatible with
legacy version 1. The app-owned advanced metadata adds an explicit travel-exception
flag; original limits and historical provenance remain stored. It never stores
Google names, addresses, hours, ratings, coordinates, route metrics or payloads.
Provider IDs remain the refresh references. Public/current details remain transient.

Existing restricted SQL identity, forced RLS, TLS, hashed capability, 30-day expiry,
receipt membership and exact selected-only writes remain. A supplied origin's
calendar is reused only after an existing approved server lookup and explicit
nearby consent; its expiring bounded memory entry stores only coordinates as the
internal lookup key plus public locality/timezone, never raw private address text.
Device coordinates and browser timezone do not establish this evidence.

No owner private profile, credential, ledger, Cloud quota, billing, paid mask,
release tag or deployment setting is changed. Hosted tests and browser cleanup
use exact generated capability hashes only; no unrelated owner plan is mutated.

## Verification and costs

The new regressions failed before repair on the exact dinner/bowling and grocery
extractions, redundant college date and absent continuation contract. The ordinary
matrix additionally covers eight source patterns in both Driving and Walking,
including single cinema, dinner/drinks, repeated/four-stop lists and retail, with
manual date/calendar/travel provenance. Existing full suites cover broader
Strict/Flexible, mall/order, hours, saving and legacy behavior.

Hosted verification: 57/57 passed, including restricted committed advanced write,
fresh-process reopen, token isolation, RLS/TLS/rollback/concurrency and exact cleanup.
Browser saved the second option from an additional advanced page, reopened only
that option in a native new tab, loaded current invented Pro facts and manual hours,
and reopened the same committed record after backend restart.

Actual browser checks use desktop 1280 and mobile 390×844. They cover the exact
college/tomorrow request; further advanced pages and explicit discovery; Previous/
Next; grocery/ATM/five-minute/45-minute return with a 20-minute grocery answer;
explicit nearby consent; strict zero-minute refusal then explicit exceptions;
ordinary Jersey City dinner/bowling and alternatives; native corrected date;
Walking regeneration; saved new-tab/restart behavior and responsive keyboard basics.
No full screen-reader audit or live Google coverage claim is made.

Measured college fixture actions: initial two searches/four Matrix cells; different
options zero searches/six additional cells; explicit discovery one search/ten
additional cells. Previous/Next and timing answers add zero calls; mode edits need
fresh evidence and add no Qwen. At the existing estimate of $0.035/Enterprise search
and $0.005/cell, those three actions represent $0.090, $0.030 and $0.085 gross.
These are reused application assumptions, not newly verified prices or posted
charges. Actual Google requests/cost for this repair: zero/$0. The separate browser
ledger accumulates synthetic requests across fixture restarts and is never reset.

Final checks: backend 892 reported / 857 passed / 35 opt-in skips; frontend 249/249;
focused 206 passed / one hosted skip; location 18/18; hosted 57/57 plus a separate
committed second-option exception proof. Build, typecheck, lint, pip/npm dependency
checks, production audit (zero vulnerabilities), secret scan and complete diff
review passed. Exact scope, corrected failures and cleanup are in HANDOVER.md. The full suite exposed
an unrelated timestamp-sensitive privacy assertion; its forced-timestamp regression
now checks coordinate structure instead of matching a latitude substring inside an
observation time. Production privacy behavior is unchanged.

Cumulative browser fixtures: 24 Enterprise searches, two Pro origin lookups,
168 Matrix cells and ten Details actions; existing synthetic gross estimate $1.944.
One browser record and the separate committed exception fixture were cleaned by
exact hashes, with committed absence verified. Temporary servers/tabs were closed
and the viewport reset; normal development servers remain healthy.

## Remaining limits

This is finite local development exploration, not unlimited discovery, citywide
exhaustion or global route optimization. Unknown/stale hours, unbounded visits,
unsupported timezone/time grammar, separate home addresses and unsupported hard
spending/accessibility/dietary/ticket requirements remain explicit limitations.
Unsaved sessions/receipts expire or disappear on restart; committed private links
remain usable until their normal expiry. Task 51 is not started.

The unchanged eight opt-in PTY lifecycle cases were not rerun; existing normal
8000/3000 servers and the homepage returned HTTP 200 after the repair. No live
Google coverage or full assistive-technology certification is claimed.
