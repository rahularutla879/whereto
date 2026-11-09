# Destination spelling investigation — November 9, 2026

Started from clean `05cfcbdbc5c36a5dfaa6478ee86b52add2260880`. The original failed outing was **not retried**. No Google Places/Routes/Geocoding, cloud AI, token-counting, billing, model/provider configuration or infrastructure action occurred.

## Original response recovery

The existing Chrome app tab still displayed its failure. Developer Tools was opened without refresh, navigation or submission. Network had no retained requests; Console retained only the failed planning HTTP 422 resource entry, not its response JSON. The app's planning client consumes that body and retains the displayed message, recovery classification and sanitized diagnostic notes, not the original full error or correlation ID. There is no persisted application log file in the checkout. The launcher inherits terminal output rather than writing a log file. Terminal-window inspection was blocked by the computer-use tool; its scrollback was not examined or bypassed.

`backend.development_diagnostics` stores only its declared fixed snapshot fields; these exclude the requested geographic rejection detail. Operational counters are process aggregates; failure logging maps unknown classifications to `other` and omits provider bodies. These cannot reconstruct the missing original response. No new diagnostic endpoint or provider call was made to try to recover it.

| Requested original field | Recovery result |
|---|---|
| `code` | Not recovered from the original response; `destination_unresolved` is reproduced offline, not claimed recovered. |
| `correlationId` | Unavailable. |
| `diagnostics.failureBoundary` | Unavailable from the original; reproduced fixture value `geography`. |
| `discoveryReasons` | Unavailable from the original; mismatch/missing-evidence fixtures both report `area_unverified`. |
| `discoveryStages` | Original counts/categories unavailable. |

No coordinates, credentials, capabilities, original request body or private origin evidence are included in this report. The original page state was left intact; no Retry or recovery button was used.

## Confirmed defect versus incident uncertainty

The exact error text originates in `backend.real_planning.real_plans` after all returned venues fail geography. Named destination matching uses provider address components, not a standalone geocoder. A local spelling comparison reproduced the error with `hitech city` requested and `HITEC City` supplied as a sublocality. Missing neighborhood evidence independently produces the same error. Therefore the spelling defect is proven, but **the original incident's precise cause remains unconfirmed**. API configuration failure and real venue availability have not been established.

Both spellings are documented by primary public sources: [Telangana Tourism's hotel entry](https://tourism.telangana.gov.in/customized-lemon-tree-hitech-city), [its hotel list](https://www.tourism.telangana.gov.in/customized-hotels), and [Cyberabad Police's Madhapur Traffic station](https://www.cyberabadpolice.gov.in/Preview?page_id=142). Their indexed official content uses both spellings in Hyderabad. Direct page fetches failed (502/timeout); this review relies on the official-source search excerpts, not a claim that every page loaded or that boundaries were verified. [Hyderabad district's Hitech City page](https://hyderabad.telangana.gov.in/gallery/it-companies/cyber-towers-hitech-city-hyderabad-3/) also identifies the spelling. Public source research did not submit user text/origin data to Maps or another inference service.

## Narrow correction

Only `backend.venue_geography.geographic_reason` changes: add the exact `hitechcity`/`hiteccity` comparison equivalence when **all** of these are supplied as provider address components:

1. Hyderabad as a locality/postal town.
2. Telangana as a state-level administrative component.
3. HITEC City or Hitech City as a neighborhood/sublocality component.

Parent city/state alone never establishes the neighborhood. The equivalence does not apply to a business display name, formatted address, premise, street, county, similarly named business or a locality-only HITEC City. It does not make Madhapur, HITEX City, My Home Bhooja or Hyderabad an alias of the requested neighborhood. No fuzzy/edit-distance matching, global normalization change or origin-based inference is added.

All remaining requested parent tokens must still match. Region exclusions, explicit radius and boundary checks run unchanged. The rule participates in the existing distant-match ambiguity check. The destination string, source evidence, original search query, confirmed origin and all activity/date/travel constraints remain unchanged. No additional query, retry, provider call, quota reset or altered threshold is introduced. This preserves existing component-based geographic safety; it does not claim polygon-level boundary proof.

## Synthetic reproduction and recovery

`backend.test_hitec_geography` uses an aware November 9 clock, November 10, 2026 date, driving mode, box cricket/dinner/movie occurrences and a **fictional origin with fictional venues and coordinates**. It does not record, verify or geocode My Home Bhooja. In the hypothetical reply containing HITEC City plus Hyderabad/Telangana components, the outing now reaches provisional planning with all three activities; unknown availability/prices/hours remain unknown. This is not a claim that a real bookable outing is available.

Nine focused test methods cover the spelling/qualified-name variants, both directions, missing/wrong parent evidence, unrelated names/brands/types, retained radius/exclusion checks, distant ambiguity, full three-stop planning, retained accounting on explicit retry, consent and strict-geography separation, and destination correction. Before the correction, the hypothetical mismatch failed after one search and zero route calls; after correction it needs three distinct initial venue searches for the three activities, without a spelling retry.

Nearby-reference use still requires explicit user selection; no consent is inferred from the confirmed origin. With missing neighborhood evidence, ordinary explicit anchor consent permits the existing approximate search behavior while retaining destination text; strict destination mode still rejects it. Correcting the destination changes only its intended geographic constraint. Backend lifecycle/frontend recovery tests retain coverage for cancellation, preferences and origin separation. No user browser recovery action was triggered for testing.

A separate loopback browser smoke used the real `/api/plans/generate` HTTP boundary with the fake providers. It returned HTTP 200, three provisional options, unchanged destination/date/driving mode and all three activities. The smoke page exposed only a sanitized summary. This was an isolated test page, **not an end-to-end retry of the owner's existing application tab or a live-Qwen/Google check**. The temporary server was stopped afterward.

## Verification and remaining limits

Final suite totals, security and journal checks are recorded in [machine-readable verification](hitec-destination-verification.json). Final complete backend discovery: **1,143 run, 1,106 passed, 37 unchanged opt-in skips, zero failures/errors** (264.155s). The preceding full run ran 1,142 tests, with 1,105 passed and 37 skips, before the ninth new method was added; all nine are included in final discovery. Frontend **285/285**, lint, TypeScript and production build passed. Configured-secret/current-assets/history scans and the three actual evaluation-key scans found zero matches. No test was skipped to conceal failure. Ordering V4 remains default OFF; the active Qwen prompt, legacy ordering behavior, saved-plan/database security and billing controls are unchanged.

All 324 private evaluation files and the original ten-row paid journal remain byte-identical, SHA256 `241af59ffa81553c98feb1e093c75194d908191504a9e67a6ad16fcc13e49028`. OpenAI 7 / Google 2 / Anthropic 1, 10/594 attempts; $0.047366625 accounted and $11.952633375 remaining. Persistent halt and original $12/594/198/12k/2k/sequential-one/no-retry limits remain intact.

No live provider request is necessary to implement or verify this constrained spelling correction. Missing provider neighborhood components still require clarification/explicit permitted recovery; they are not fixed by aliasing. Real provider responses, origin geometry and availability remain unverified. If a later incident persists, inspect already-retained error diagnostics first; any new live request requires separate payload/cost authorization. No additional live request is proposed or authorized by this change.
