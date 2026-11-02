# Tasks 46/49: regeneration, saved preferences and hours preparation

November 2, 2026. Acceptance repair only; Task 50 and Tasks 50A–50E remain unstarted.

## Reproduction and repair

Repeated fresh planning dispatches bounded new searches/routes and consumes the shared
allowance even when only Strict/Flexible or mode changes. Before this repair,
`ProviderLimitError` had no `code`; `provider_code()` consequently returned
`provider_service_error`. A local ten-search/minute denial was presented as a
failed venue/routing service. This is a reproduced classification defect, not proof
that every historical owner failure had this cause. In a controlled identical-payload
comparison, both regeneration and the post-refresh request failed under the same
filled shared window. A page refresh does not clear admission; elapsed time can
explain apparent recovery. No owner ledger or limits were reset.

Process search/matrix minute exceptions now carry a fixed local-minute reason and
earliest window-reset estimate (not a promise that an entire batch will fit). Planning responses distinguish local temporary admission,
other local safeguards, Cloud quota rejection and actual provider failure. Correlation
IDs remain opaque; no SQL/provider bodies/credentials are returned. No automatic retry
is added. Other admission failures advise inspecting local diagnostics rather than
claiming venue scarcity. Existing continuation-specific resumable handling remains.

The origin editor also returned the earlier interpreted `betweenTravel` in origin mode,
even after its editor value changed. It now returns the current owned value, including
explicit null removal, matching Surprise Me. Existing FirstPreference manual precedence,
origin confirmation and mode-specific evidence guards remain. A regeneration is a fresh
planning request/context, not an options continuation. The validated interpretation
continuation is only for grounded parsing; it is not a venue-search session. Old
options/evidence/pages cannot be reused after configuration edits. Scoring weights,
discovery architecture, constraints and quotas are unchanged.

## Saved UI

Travel mode no longer repeats “optional.” Current real-result badges say Real venues;
shared availability/schedule warnings and Google credit remain. Saved-link actions share
a wrapping flex group, 12-pixel gaps and 44-pixel minimum height; Forget is secondary.
After a confirmed commit the selector/save control is replaced by one “Your plan is
saved” heading, one expiry/sharing sentence and Copy/Open/Forget. Copy feedback remains
separate. A retained old link is explicitly labeled Previously saved plan while another
outing is unsaved. Failed saves never install an unconfirmed link. An in-flight guard
prevents double-click submissions; an epoch guard excludes stale save feedback after
configuration changes. Existing idempotent backend save and stored alternatives remain.

Saved preferences use a collapsed definition list for date/window, destination/timezone,
mode, first/between limits, ordered activities, origin availability, requirements and
budgets. Exclusive legacy limits retain “under”; Flexible retains its doubled maximum.
The checkbox reads Include phone number and website; its opt-in Enterprise behavior
and automatic Pro-only loading are unchanged.

The default 10 AM start (or rounded current local minute for today) and end-of-date
midnight are planning boundaries, not a confirmed arrival or user-specified end time.
The persisted explicitStart/explicitEnd flags now explain defaults. 1440 means midnight
at the **end of the saved date**, not 00:00 at its beginning. Explicit overnight requests
still require clarification; the single-day planner does not silently extend them.
Unknown legacy flags are not invented. No temporal constraint is changed or hidden.

## Exploration

Show different options recombines known places (bounded missing-route verification can
still be needed), without new Places discovery. Search more nearby places performs
bounded distinct discovery with unchanged original limits. Show options beyond my
limit is an explicit exception view; the immutable request/preference remains unchanged,
and per-option deviations remain visible. Each control has one concise description.
Original page history, complete-itinerary uniqueness, pending-route/exhaustion/admission
states and ranking are preserved. No automatic widening is introduced.

## Hours: current evidence and approval boundary

Live search's current Pro mask contains identity, address/location, types, attributions
and paging; its existing separately gated Enterprise extension adds rating/count only.
Saved Pro Details includes businessStatus; explicit contact Enterprise adds phone and
website. **None currently requests opening hours or venue timeZone. Operational is not
proof of being open.** No current real itinerary guarantees opening at the visit time.

The existing pure normalizer and feasibility evaluator already preserve supplied dated
current periods, special days, field-level observation times, venue IANA timezone and
request-date coverage. They verify the entire arrival/departure interval using dated
current periods within a fresh seven-day coverage window. They conservatively return
unverified for missing schedule/durations/timezone, stale/truncated/ambiguous periods,
regular-hours-only evidence or future dates outside current coverage. They handle
midnight-spanning/adjacent periods, DST and the documented 24-hour sentinel. Regular
weekday schedules alone never establish a holiday exception. Today's openNow is never
used to prove future availability. Even covering hours cannot verify tickets/events,
screenings/reservations or activity participation. Unknown real stop durations prevent
invented downstream arrival windows. Existing offline evaluator behavior is retained
and exercised with additional acceptance fixtures; it is not silently connected to
live candidate eligibility without real schedule/hours evidence.

Reviewed official [Place Details fields](https://developers.google.com/maps/documentation/places/web-service/place-details),
[Place/OpeningHours reference](https://developers.google.com/maps/documentation/places/web-service/reference/rest/v1/places),
[global prices](https://developers.google.com/maps/billing-and-pricing/pricing) and
[Places policies](https://developers.google.com/maps/documentation/places/web-service/policies).
A proposed future **selected-only** Details mask is
`id,displayName,formattedAddress,businessStatus,googleMapsUri,attributions,timeZone,currentOpeningHours,regularOpeningHours`.
Secondary hours are inappropriate unless the request actually targets that separate
service. `timeZone` is Pro; current/regular opening hours trigger Details Enterprise.
No separate Time Zone API is proposed. Current hours include special-day adjustments
and cover seven days from the request, including today; limited coverage/truncated
periods are not extended into an invented future schedule.

At the first paid global tier Details Enterprise is $20/1,000 requests versus Pro
$17/1,000, before SKU-specific allowances: two selected stops cost $0.04 gross, four
$0.08; incremental tier difference $0.006/$0.012 if replacing the same Pro requests.
A separate later hours action incurs its own full request cost. Contact Details already
uses Enterprise, but authorization for contacts does **not** authorize hours. Existing
rating-enabled Text Search is Enterprise ($35/1,000 versus Pro $32/1,000); do not add
hours to every search despite a possible unchanged tier. No quotas or billing settings
change, and posted/free-tier costs can differ from conservative local estimates.

**Additional owner approval is required before any live hours field is enabled.**
Proposed staged work: evaluate only shortlisted/selected original stops (at most four
unique references), within existing shared Details ten/minute and last-verified Cloud
40/day, no retries, with minimal per-action evidence kept only in memory. Ask for an
explicit date/window when needed; do not fan out across every discovered candidate.
Future integration must account for all requests and preserve original saved stops if
verification fails. This proposal is documented only: no new field, operation, gate or
paid request was enabled in this repair. No schema migration is needed.

## Verification

See the final HANDOVER checkpoint for actual suite totals, hosted rollback/cleanup and
browser results. All Google-shaped tests use invented fixtures; network dispatch is
forbidden. No owner records, Cloud settings, real ledger or restricted provider content
were modified. Public deployment, live hours checking, bookings, full accessibility
auditing and later roadmap security work remain outside this acceptance pass.

Final verification: backend **660 run /640 passed /20 hosted skips**; frontend
**226/226**; separate hosted **37/37** (20 real PostgreSQL rollback checks +17 offline).
TypeScript, lint, production build and Python dependency consistency passed. A committed
selected walking browser plan was reopened, independently verified and exactly cleaned.
Desktop1280/mobile390 layouts, Strict/Flexible/mode changes, actual shared-window recovery
without reload, pages2/3, subsequent regeneration and copy/new-tab behavior were exercised.
Screenshots and detailed evidence are recorded in HANDOVER.md. No live Google calls.
