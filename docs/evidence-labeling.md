> Task 46 now connects these components to the existing local planner. Mock remains default; real mode and contact lookups require deliberate switches. [Current flow, safeguards and closed live ledger](real-planning.md). Sections below preserve earlier task checkpoints.

# Task 45 — source and verification labels

`backend/evidence.py` is a pure, transient adapter layer. It reads existing Task
40–44 models without changing their schemas, making provider calls, or changing
the fictional planner. No endpoint or frontend integration is added.

## Contract

`EvidenceLabels.claims` maps field paths to `Claim` objects. Each claim separates:

- `source`: kind (`provider`, `local`, `user`, `fixture`, `unknown`), original
  provider/Place ID when applicable, optional reference and source URL.
- `certainty`: the meaning of the evidence, independent of source identity.
- `basis`: `supplied`, `computed`, `not_retrieved`, `not_checked`, or `fixture`.
- `message`: short display text. `observed_at` is a local receipt timestamp,
  not independent verification or a freshness guarantee. `explicit_dates` records
  supplied period endpoint or exception dates; it never establishes full coverage.
- `contributing_sources`: original observations supporting a merged field.

| Certainty | Meaning |
| --- | --- |
| `reported` | A supplied fact or an explicitly scoped computed check result; inspect source and basis. No real-world guarantee. |
| `estimated` | A calculated approximation, including provider routing. |
| `provisional` | Supplied but time-dependent or limited in applicability. |
| `unknown` | No usable value/evidence; never false, free, zero, closed or sold out. |
| `requires_confirmation` | Availability or reservation needs confirmation. |
| `fictional` | Explicit development fixture evidence. |
| `unverified` | Not checked or insufficiently supported. |

No whole-venue/whole-itinerary verified flag, confidence percentage or score is
introduced. Existing legacy `DataQuality` and `VenueFacts.evidence` remain compatible;
their coarse fields must not replace the new field labels for real content.

## What the available evidence supports

Current Places Pro discovery requests only ID, display name, address, location,
geographic address components and attributions. `venue_labels(VenueFacts)` marks
identity/name/address/coordinate components as provider-reported, not independently
verified. Activity is local search context; Task 42 relevance remains a separate
decision. Geographic acceptance is not proof of event/booking availability.

Optional ratings/counts, hours, websites, Maps links, prices and timezone are
already supported by Task 41 normalization, but are **not requested by today's
mask**. Missing fields say unavailable or not retrieved; this model cannot tell
whether a provider has no information without an actual response/request history.
Business status is not currently normalized and stays not retrieved. A future
authorized mapper may add fields using the same claim structure. Enterprise-style
synthetic enrichment is tested; no Enterprise fields or Details calls are requested.

Nested facts have individual labels/timestamps, including missing nested fields.
Partial updates retain original receipt times of unchanged evidence. Empty supplied
hours periods and `openNow=false` are supplied information, distinct from null.
`openNow` is not a future-date closure and never establishes session availability.
`distinct_venue_labels(DistinctVenue)` preserves original contributing Place IDs,
source links and combined credits after Task 42 merging; use it for merged records.
Original observations remain in `DistinctVenue.sources` for backend review.

Regular hours are provisional and explicitly warn about holidays/exceptions.
Current hours are provisional date-specific evidence; supplied endpoint/exception
dates are retained. According to the [official Place reference](https://developers.google.com/maps/documentation/places/web-service/reference/rest/v1/places#OpeningHours),
current hours cover seven days beginning on the request date. Do not infer that
date from a receipt timestamp. Task 44 requires explicit `hours_request_date`,
timezone, complete periods, receipt freshness and a visit inside that window before
confirming/rejecting hours. Stale, truncated, ambiguous or insufficient evidence
remains unverified. Task 45 does not independently decide date applicability.

Price levels/ranges are provider indicators, never exact per-person/ticket quotes.
An explicit free category does not establish that an outing, extras or session is
free. Precise outing price remains unknown even with a price indicator. Cinema
hours do not prove a showtime; restaurant hours do not prove reservation inventory.
Activity sessions stay unverified and availability requires confirmation.

## Travel and feasibility

`route_labels(RouteLeg)` labels both duration and distance as estimates. Pair these
labels with the original leg, which retains direction, transport mode, provider,
estimate type, exact seconds/nanoseconds/meters and status. Current driving uses
`traffic_unaware`, never live traffic; walking carries the beta/pedestrian-path
warning. Neither promises arrival. Same-location transitions are local identity
calculations, with no Google attribution claim. Missing/error metrics stay null;
Google's explicit no-route result is reported separately from unknown metrics.

`feasibility_labels(FeasibilityResult)` translates Task 44 results without rerunning
or duplicating its evaluator. It preserves each check's state, kind and stop index.
The paired original result retains exact codes/evidence references for backend
review; the display contract excludes these internal structures. Fixed message
templates never interpolate raw errors, provider payloads, coordinates or tokens.
Unknown future codes receive conservative generic wording.

Feasible means only that checked travel/hours constraints satisfy available
evidence. Estimates remain estimates. An infeasible result preserves proven
violations even alongside unknown facts; it does not verify the rest of the plan.
The display scope always says prices, reservations and availability are unverified.
Task 46 must still apply all other planner constraints and retain provisional
outcomes whenever relevant mandatory evidence is missing.

`fictional_labels(Venue)` uses existing fixture metadata and preserves missing
values as unknown. It requires explicitly fictional identity, handles scheduled
fixtures, and never adds Google branding. `user_detail_label()` identifies
user-entered information without independently verifying it. The current mock UI,
disclosures and serialized planner outputs remain unchanged.

## Attribution and source links for Task 46

Reviewed the current official [Places policies](https://developers.google.com/maps/documentation/places/web-service/policies)
and [Routes policies](https://developers.google.com/maps/documentation/routes/policies)
on October 24, 2026. The updated attribution sections govern new implementations;
their page-summary references to the older Google logo do not supersede them.
Account-specific agreements and billing location govern; EEA terms differ.

`DisplayAttribution` carries the Google Maps brand requirement, logo preference,
limited-space text allowance, applicable policy URL, supplied third-party credits
with their URIs, and route notices. The contract prepares display; it does not by
itself fulfill visual/legal requirements. Task 46 must:

- Keep attribution visible, legible, near the content in the same container, and
  distinguish Google content from fictional/user/local content. Prefer official
  unmodified Google Maps logo assets. If space requires text, use the exact
  untranslated, unwrapped `Google Maps` name and documented typography/contrast.
- Display supplied third-party credits alongside their content, preserving links.
  Google branding alone is insufficient when third-party credits are supplied.
- Supply attribution when displaying content without a map. No interactive map or
  Maps JavaScript API is required. If mapped later, use a Google map and preserve
  included attribution. Publish the required Terms of Use/Privacy Policy before
  public Google-content use. Review any later photos/reviews separately; none are
  requested or retained here.

Preserve a supplied `googleMapsUri` unchanged. If absent, `venue_source` builds
only the [official documented Maps search URL](https://developers.google.com/maps/documentation/urls/get-started#search)
using encoded `api=1`, place name and original `query_place_id`, subject to its
2,048-character limit. Link origin distinguishes provider versus documented URL;
constructing it makes no API request and establishes no availability. Websites and
credit URIs remain in the existing models. No route source URL is fabricated:
Compute Route Matrix supplies no source-link field in the current mask.

## Privacy, retention and verification

All provider values and labels remain transient in memory. Do not persist these
objects, provider source URLs, evidence timestamps or itinerary snapshots as a
workaround for restricted-content storage. Place IDs have a retention exception;
the applicable non-EEA terms allow limited coordinate caching, not whole-record
storage. Task 41's [retention boundaries](venue-discovery.md) remain applicable;
no cache is introduced. Review permissions before any future persistence feature.

No provider masks, quotas, limits, alerts, billing plan, authentication, prices or
default gates changed. No live Places/Routes calls, token refreshes or Cloud
administration occurred. Tests use invented responses with socket/transport/auth
guards. Existing catalog/output fingerprints verify fictional planner compatibility.
Task 46 will attach these adapters and attribution requirements to real-data
planning/UI while retaining mock mode. Task 46 has not started.
