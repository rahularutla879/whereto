# Final UI cleanup and Driving/Walking acceptance

November 2, 2026. Continues clean `990cccf`. This is an acceptance refinement and
one travel-mode control, not Task 50 or Tasks 50A–50E. No discovery/ranking rewrite,
new provider service, migration, credentials change, quota change or billing change.

## Ten UI cleanup changes

1. Header retains branding and one **How it works** native new-tab link to
   `/how-it-works`; **A little demo** is removed. The mobile rule that previously
   hid the first header link was removed so the guide remains accessible.
2. Footer **Give it a go** anchor and its containing demo section are removed.
3. Form guidance is now “Not finding what you’re looking for? Try adjusting your
   preferences or searching again.” It is absent while loading, disconnected,
   clarifying, failing or showing an empty result with a specific explanation.
4. Form mock/real/development badges are removed. Mode remains available on the
   guarded `/dev/diagnostics` page. Result provenance, provisional labels and
   required Google attribution remain.
5. Supported activities keeps the shared registry, examples and meaningful
   schedule/participation limitations, without mock/provider-configuration prose.
6. **A small demo. A big idea.** and the lengthy technical demo footer are removed.
7. One understated footer paragraph explains that Where To? is still growing.
8. **Try an example** and its handler are removed. The natural-language placeholder,
   input, follow-ups and ordinary planning controls remain.
9. Privacy and Terms use native `_blank` links with noopener/noreferrer. Both pages
   now use a restrained readable information-page layout, section headings and
   shorter paragraphs. Existing substantive location, storage, consent, provider
   and private-link disclosures are retained. Privacy now accurately distinguishes
   ordinary startup (no saved-details retrieval) from owner-enabled deliberate
   saved-link opens/reloads (bounded automatic Pro). Enterprise contact choice
   remains explicit; no universal/production automatic retrieval is claimed.
10. The blanket fictional-data sentence is removed. Fictional example disclosure
    stays beside actual example cards; generated mock results keep their own
    truthful labels. Real results retain attribution and evidence limitations.

The guide explains requests, destination/origin, current/manual/Surprise Me starts,
optional preferences, both modes, Strict/Flexible, card details, pagination,
combinations versus discovery, saving/selection/copying/opening/shared links,
supported activities, uncertainty and recovery. It contains no architecture,
provider budgets, model names or developer flags. No bookings, live hours,
showtimes, inventory, route safety or venue availability are promised.

## Mode contract and propagation

The existing `transport` field is reused. The preference control displays Driving
by default, with Walking selectable. An untouched default is not a manual override
of clear walking intent in the request. Explicit selection is retained through
unrelated preference edits, follow-ups, regeneration and the active continuation.
Changing mode invalidates the old displayed results and requires regeneration.

`ManualPreferences.transport` accepts empty/unselected, driving or walking.
Public `PlanningRequest`/`PlannerInput` default omitted or legacy null transport to
driving and reject unsupported modes. The broader historical `OutingRequest` and
AI enum remain compatible with existing internal/legacy representations; they do
not enable cycling or transit routing. A small grounded mode resolver handles
clear source wording and explicit selection without asking Qwen to guess a chosen
mode. Conflicting UI/text or mixed-mode requests block with an actionable message.
Bare absent optional-mode uncertainty does not trigger another model guess. Public OpenAPI advertises exactly the same two accepted values. A selected mode never masks a separately requested walk activity.
Unrelated model grounding and unsupported-activity checks remain in force.

The effective request mode reaches origin confirmation/preflight, the existing
shortlisting, directed first/inter-stop matrix requests, feasibility, scoring and
continuations. Existing mode-aware discovery heuristics are reused. Candidate
normalization, Places query architecture, beam structure, weights, diversity,
three-card history, full-itinerary uniqueness and Strict/Flexible rules are unchanged.

A route cache remains local to its immutable active outing: pair keys are guarded
by an explicit context mode and every retained leg's mode. Mutated/mixed contexts
are rejected, not reused. Existing matrix reservation hashes include `travelMode`;
feasibility matches origin, destination and mode. The frontend also rejects a
response labeled with evidence from a different mode. No cross-mode/cross-user
response cache is added. Missing walking routes remain unknown, never driving
fallbacks or zero-minute estimates.

Strict 10 minutes checks the selected mode's exact route duration. Flexible 10
prefers 10 and retains its existing inclusive 20-minute maximum. Miles preferences
use the selected mode's verified route distance; straight-line search heuristics
never establish compliance. Expanded travel exceptions still require existing
explicit authorization and keep their warnings.

## Google operation, warning and costs

Reviewed [matrix modes](https://developers.google.com/maps/documentation/routes/vehicles-rm),
[matrix options](https://developers.google.com/maps/documentation/routes/options-rm),
[request limits](https://developers.google.com/maps/documentation/routes/compute_route_matrix),
[billing](https://developers.google.com/maps/documentation/routes/usage-and-billing)
and [attribution](https://developers.google.com/maps/documentation/routes/policies).

Both modes use the existing authorized `distanceMatrix/v2:computeRouteMatrix`
operation: driving sends `DRIVE` plus `TRAFFIC_UNAWARE`, walking sends `WALK` and
no unsupported traffic preference. The exact minimal mask remains
`originIndex,destinationIndex,status,condition,distanceMeters,duration`.
No advanced features or new paid tier are enabled. The documented limits are
625 non-transit cells and at most 50 combined address/Place-ID waypoints; existing
smaller staged application limits, admission, zero retries and project quotas stay.

Billing remains per matrix element, not per card or dropdown change. Only the
selected mode is calculated, with no speculative second-mode requests. The fixed
three-candidate regression reserves 12 cells for each mode. Actual discovery and
eligible paths may differ by mode, so equal counts are not a universal guarantee.
Changing mode/regenerating is new bounded work and consumes existing capacity.
No Cloud quotas, billing configuration, credentials or owner ledger were modified.

Cards and expanded details name the mode and distinguish the first journey from
inter-stop travel. One shared walking notice states that routes are in beta and
may omit sidewalks/pedestrian paths, without claiming safety/accessibility. Google
attribution remains. Fictional simulation remains mode-independent and is labeled
as simulation, not verified driving or walking.

## Persistence and compatibility

The existing `plan_constraints.transport` column stores the normalized app-owned
mode. New saved plans retain it; old null/missing mode reads default to the original
driving behavior without updating owner records. Other legacy preferences are not
silently relabeled as driving. Selected-only presentation, ordered original Place
IDs, capability security/expiry, restricted runtime role, forced RLS and TLS remain.
No migration is needed. Google route data remains excluded from persistence;
saved mode is a planning preference, not permission to display historical metrics.
Current Place Details refresh and its existing Pro/Enterprise gates are unchanged.

## Verification evidence

- Full backend: **646 run, 626 passed, 20 hosted skips**, 175.669s. Full frontend: **222/222**, 117.401s. Focused modes/models/interpretation/validation: **67/67**. TypeScript, ESLint, production build and Python dependency checks passed.
- Thirteen targeted backend mode tests cover defaults, null/invalid inputs, explicit
  choices, source conflicts/negation, optional-mode uncertainty, deterministic
  follow-up, origin/inter-stop differences, both Strict/Flexible scopes, mode-based
  distances, missing evidence, mode-separated continuation/cache/request hashes,
  uniqueness, matrix accounting and safe persistence mapping.
- Frontend tests cover preference state and payload propagation using actual offline
  Python-planner results, mixed-mode rejection, labels, shared warning, legacy saved
  modes, new-tab markup, guide/legal content and all removed product copy.
- Hosted **37/37** passed: **20 actual PostgreSQL rollback tests plus 17 offline
  checks**, 16.554s. Includes new walking-column and legacy-null round trips,
  existing transaction/rollback/capability/grant/RLS checks. No owner records changed.
- Browser: at 1280 pixels, driving first journeys fit Strict 10; the same origin's
  12-minute-plus walking journeys are withheld under Strict and appear under Flexible
  10/max20 with exact excess labels. Walking inter-stop cards show 15/16 minutes
  versus driving's approximately five, with walking text in View plan. Different
  options and nearby exploration retain mode and advance page history.
- Native guide/Privacy/Terms tabs preserve the original request, all three cards and
  page 3. Guide/legal layouts, mode control, keyboard focus, walking results and saved
  view were checked at 390 pixels with no horizontal overflow. An actual UI/text
  conflict blocks; correcting it retains Walking and produces walking results.
- A committed selected-option-2 walking plan reopened in a new tab with current
  invented Details and the original mode/order. Independent SQL verified the mode,
  three retained alternatives, ordered stops and no provider snapshots. Only that
  exact hashed fixture was deleted, followed by an independent committed-cleanup
  check. Existing owner plans and the two-entry migration ledger were preserved.
- Offline browser counts: 19 searches, 76 matrix elements, two Details, three AI
  fixture extractions. A shared ten-search/minute admission pause recovered after
  its window; no usage reset or limit increase. Actual Google sends/charges: zero.

Limits: no live walking coverage/accuracy test was performed. Provider coverage and
quotas can still block a route/search; no fallback driving evidence is used. Mock
travel remains an explicitly fictional mode-independent simulation. Mixed modes,
cycling/transit, return journeys and advanced journey requirements are not added.
Full assistive-technology auditing and public deployment remain outside this pass.
Tasks 50 and 50A–50E remain unstarted.

Final cleanup restored the ordinary real-profile backend on port8000. Backend and Next.js health checks and the restricted authenticated TLS checker are recorded in HANDOVER.md. Temporary browser tabs were closed, responsive override reset and remembered disposable link forgotten. No owner data or live ledger was reset.
