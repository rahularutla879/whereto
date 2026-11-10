# Q4A independent semantic and implementation review — UNSIGNED

No approval is recorded. Complete this package independently of the rubric/implementation author. Same-agent tests are not signoff. Amend frozen expectations only through a separately reviewed version.

Parent: `52b-q3-openai-b2-v4-guarded-PROPOSED-v1`. Parent configuration: `850ad650bff6bab9c4465e657932874cbcae06a9a7b4e1c79eda8891a6eb942b`. Execution manifest SHA256: `8406905232a36726c17960d56cf66527edd79111750530871502378c711275c1`. Purpose: offline review candidate; no paid authority.

Reviewer name: __________  Independent of author: __________  Date/time: __________
Implementation/security review decision: __________  Scope/financial owner approval: **not granted by this worksheet**.

For each field record agree/disagree/unresolved plus evidence; N/A is a required absence check. Every applicable and absence assertion must be reviewed. Any disagreement blocks that slot. Review source occurrence ownership, not only words or graph shape. No future response is approved here.

## 1. extension-repeated/r2

> Coffee, museum, then coffee in Jersey City tomorrow, return to the starting point within three hours.

Source hash: `7183ad071492d60d68a65a12f2e6b8cbdf77d25efdf1dc2e466152ca9d42bd6c`. Rubric hash: `77940447f4e618c1560b010e6cc61f2c3253543092c7f0c596c823339c703920`.

| Q1 field | Applicability | Frozen expectation | Judgment / evidence |
|---|---|---|---|
| required_activities | supported | [{"id":"s0","index":0,"sourcePhrase":"Coffee","requirement":"required"},{"id":"s1","index":1,"sourcePhrase":"museum","requirement":"required"},{"id":"s2","index":2,"sourcePhrase":"coffee","requirement":"required"}] | __________ |
| optional_activities | not_applicable | Absent: invention fails | __________ |
| exact_named_identity | not_applicable | Absent: invention fails | __________ |
| mandatory_order | supported | {"requiredReachability":[[1,2]],"forbidAllOtherNontransitiveEdges":true,"indexBasis":"source occurrences; list position alone is not mandatory order"} | __________ |
| unordered_flexible | supported | {"mode":"partial","independentOccurrences":[0],"noFullSequenceFromList":true} | __________ |
| repeated_stops | supported | [{"phrase":"Coffee","indices":[0,2]},{"phrase":"coffee","indices":[0,2]}] | __________ |
| return_origin | supported | {"required":true,"needsConfirmedOriginBeforePlanning":true,"noInferredCoordinates":true} | __________ |
| final_destination | not_applicable | Absent: invention fails | __________ |
| final_visit | not_applicable | Absent: invention fails | __________ |
| home_ambiguity | not_applicable | Absent: invention fails | __________ |
| whole_trip_limit | supported | {"minutes":180,"relation":"maximum","scope":"whole outing; include return only if independently required","inclusive":true} | __________ |
| travel_only_limit | not_applicable | Absent: invention fails | __________ |
| visit_durations | not_applicable | Absent: invention fails | __________ |
| duration_relations | supported | [{"scope":"whole_trip","minutes":180,"relation":"maximum"}] | __________ |
| dates_timezones | supported | {"expressions":["tomorrow"],"syntheticCalendarTimezone":"America/New_York","referenceTime":"2026-11-05T15:00:00Z","resolvedDateIfKnown":"2026-11-06","unknownTimezoneAction":"clarify before planning; retain expression","noInventedTimeWindow":true} | __________ |
| budget_transport | not_applicable | Absent: invention fails | __________ |
| safe_disposition | supported | {"extraction":"preserve all applicable fields","planning":"clarify unresolved required location/date/origin/identity; otherwise normal validated handoff, not a venue-availability promise","semanticClarification":[],"safeRejectionAllowedOnlyForUnsupportedOrContradictoryInstructions":false} | __________ |
| hallucinations | supported | {"forbidden":"Any mandatory activity, venue identity, edge, endpoint, date/time, duration, price, availability or capability unsupported by original source or explicit fixture context. Null/default is not permission to guess.","doNotDropUnknownActivities":true} | __________ |
| contradiction_injection | not_applicable | Absent: invention fails | __________ |
| source_provenance | supported | {"occurrenceIDs":["s0","s1","s2"],"sourceSpanOwnership":"verbatim/bounded supported normalization and correct occurrence; borrowed or mismatched evidence fails","emptyGoldEvidence":"unspecified exact quote, never evidence optionality","explicitGoldEvidence":"retain exact asserted nonempty reference value; source grounding still required","edgeEvidence":"both referenced phrases and attached directional cue, independently proved; substring alone insufficient","requiredFields":"wire-schema required/null contract; missing property differs from explicit null"} | __________ |
| people | not_applicable | Absent: invention fails | __________ |
| geography | supported | {"destinationText":"Jersey City","noOriginSubstitution":true,"noSilentWidening":true} | __________ |
| shared_place | not_applicable | Absent: invention fails | __________ |
| deadline | not_applicable | Absent: invention fails | __________ |

Complete independent gold decision: __________  Date/signature: __________
Future response hash: __________  Raw24-field decision: __________  Legacy decision: __________  Guarded decision: __________
Occurrence/mapping and expected clarification checked: __________  Disagreement/unresolved notes: __________
Separate independent per-response signoff/date (only after response): __________

## 2. journey-04/r2

> Go to SUNY College of Optometry and then get coffee.

Source hash: `608d5f41198d2d658bc288520dc8513eef6f2419d3779fb6ecd87137297d450e`. Rubric hash: `802608fa6fb46b4769d2de3f1fa99271b0c02d87bd8af96429b17871cb84b6d8`.

| Q1 field | Applicability | Frozen expectation | Judgment / evidence |
|---|---|---|---|
| required_activities | supported | [{"id":"s0","index":0,"sourcePhrase":"SUNY College of Optometry","requirement":"required"},{"id":"s1","index":1,"sourcePhrase":"coffee","requirement":"required"}] | __________ |
| optional_activities | not_applicable | Absent: invention fails | __________ |
| exact_named_identity | supported | [{"index":0,"kind":"named_place","identity":"SUNY College of Optometry","unresolved":false}] | __________ |
| mandatory_order | supported | {"requiredReachability":[[0,1]],"forbidAllOtherNontransitiveEdges":true,"indexBasis":"source occurrences; list position alone is not mandatory order"} | __________ |
| unordered_flexible | supported | {"mode":"constrained","independentOccurrences":[],"noFullSequenceFromList":true} | __________ |
| repeated_stops | not_applicable | Absent: invention fails | __________ |
| return_origin | not_applicable | Absent: invention fails | __________ |
| final_destination | not_applicable | Absent: invention fails | __________ |
| final_visit | not_applicable | Absent: invention fails | __________ |
| home_ambiguity | not_applicable | Absent: invention fails | __________ |
| whole_trip_limit | not_applicable | Absent: invention fails | __________ |
| travel_only_limit | not_applicable | Absent: invention fails | __________ |
| visit_durations | not_applicable | Absent: invention fails | __________ |
| duration_relations | not_applicable | Absent: invention fails | __________ |
| dates_timezones | supported | {"expressions":[],"syntheticCalendarTimezone":"America/New_York","referenceTime":"2026-11-05T15:00:00Z","resolvedDateIfKnown":null,"unknownTimezoneAction":"clarify before planning; retain expression","noInventedTimeWindow":true} | __________ |
| budget_transport | not_applicable | Absent: invention fails | __________ |
| safe_disposition | supported | {"extraction":"preserve all applicable fields","planning":"clarify unresolved required location/date/origin/identity; otherwise normal validated handoff, not a venue-availability promise","semanticClarification":[],"safeRejectionAllowedOnlyForUnsupportedOrContradictoryInstructions":false} | __________ |
| hallucinations | supported | {"forbidden":"Any mandatory activity, venue identity, edge, endpoint, date/time, duration, price, availability or capability unsupported by original source or explicit fixture context. Null/default is not permission to guess.","doNotDropUnknownActivities":true} | __________ |
| contradiction_injection | not_applicable | Absent: invention fails | __________ |
| source_provenance | supported | {"occurrenceIDs":["s0","s1"],"sourceSpanOwnership":"verbatim/bounded supported normalization and correct occurrence; borrowed or mismatched evidence fails","emptyGoldEvidence":"unspecified exact quote, never evidence optionality","explicitGoldEvidence":"retain exact asserted nonempty reference value; source grounding still required","edgeEvidence":"both referenced phrases and attached directional cue, independently proved; substring alone insufficient","requiredFields":"wire-schema required/null contract; missing property differs from explicit null"} | __________ |
| people | not_applicable | Absent: invention fails | __________ |
| geography | not_applicable | Absent: invention fails | __________ |
| shared_place | not_applicable | Absent: invention fails | __________ |
| deadline | not_applicable | Absent: invention fails | __________ |

Complete independent gold decision: __________  Date/signature: __________
Future response hash: __________  Raw24-field decision: __________  Legacy decision: __________  Guarded decision: __________
Occurrence/mapping and expected clarification checked: __________  Disagreement/unresolved notes: __________
Separate independent per-response signoff/date (only after response): __________

## 3. extension-partial/r2

> Visit a pharmacy before the bank; get coffee whenever convenient, in Jersey City tomorrow.

Source hash: `4038a95c47f7fc546989b1ed84ef43aac9fd586a18ad2a06c1e6d0415e42497f`. Rubric hash: `eebc83d5f13adc1d83bc2ac95a38125c2d8ceb228d5b2fd2a66b83013ce86db1`.

| Q1 field | Applicability | Frozen expectation | Judgment / evidence |
|---|---|---|---|
| required_activities | supported | [{"id":"s0","index":0,"sourcePhrase":"pharmacy","requirement":"required"},{"id":"s1","index":1,"sourcePhrase":"bank","requirement":"required"},{"id":"s2","index":2,"sourcePhrase":"coffee","requirement":"required"}] | __________ |
| optional_activities | not_applicable | Absent: invention fails | __________ |
| exact_named_identity | not_applicable | Absent: invention fails | __________ |
| mandatory_order | supported | {"requiredReachability":[[0,1]],"forbidAllOtherNontransitiveEdges":true,"indexBasis":"source occurrences; list position alone is not mandatory order"} | __________ |
| unordered_flexible | supported | {"mode":"partial","independentOccurrences":[2],"noFullSequenceFromList":true} | __________ |
| repeated_stops | not_applicable | Absent: invention fails | __________ |
| return_origin | not_applicable | Absent: invention fails | __________ |
| final_destination | not_applicable | Absent: invention fails | __________ |
| final_visit | not_applicable | Absent: invention fails | __________ |
| home_ambiguity | not_applicable | Absent: invention fails | __________ |
| whole_trip_limit | not_applicable | Absent: invention fails | __________ |
| travel_only_limit | not_applicable | Absent: invention fails | __________ |
| visit_durations | not_applicable | Absent: invention fails | __________ |
| duration_relations | not_applicable | Absent: invention fails | __________ |
| dates_timezones | supported | {"expressions":["tomorrow"],"syntheticCalendarTimezone":"America/New_York","referenceTime":"2026-11-05T15:00:00Z","resolvedDateIfKnown":"2026-11-06","unknownTimezoneAction":"clarify before planning; retain expression","noInventedTimeWindow":true} | __________ |
| budget_transport | not_applicable | Absent: invention fails | __________ |
| safe_disposition | supported | {"extraction":"preserve all applicable fields","planning":"clarify unresolved required location/date/origin/identity; otherwise normal validated handoff, not a venue-availability promise","semanticClarification":[],"safeRejectionAllowedOnlyForUnsupportedOrContradictoryInstructions":false} | __________ |
| hallucinations | supported | {"forbidden":"Any mandatory activity, venue identity, edge, endpoint, date/time, duration, price, availability or capability unsupported by original source or explicit fixture context. Null/default is not permission to guess.","doNotDropUnknownActivities":true} | __________ |
| contradiction_injection | not_applicable | Absent: invention fails | __________ |
| source_provenance | supported | {"occurrenceIDs":["s0","s1","s2"],"sourceSpanOwnership":"verbatim/bounded supported normalization and correct occurrence; borrowed or mismatched evidence fails","emptyGoldEvidence":"unspecified exact quote, never evidence optionality","explicitGoldEvidence":"retain exact asserted nonempty reference value; source grounding still required","edgeEvidence":"both referenced phrases and attached directional cue, independently proved; substring alone insufficient","requiredFields":"wire-schema required/null contract; missing property differs from explicit null"} | __________ |
| people | not_applicable | Absent: invention fails | __________ |
| geography | supported | {"destinationText":"Jersey City","noOriginSubstitution":true,"noSilentWidening":true} | __________ |
| shared_place | not_applicable | Absent: invention fails | __________ |
| deadline | not_applicable | Absent: invention fails | __________ |

Complete independent gold decision: __________  Date/signature: __________
Future response hash: __________  Raw24-field decision: __________  Legacy decision: __________  Guarded decision: __________
Occurrence/mapping and expected clarification checked: __________  Disagreement/unresolved notes: __________
Separate independent per-response signoff/date (only after response): __________

## 4. journey-06/r2

> Buy groceries and maybe stop for coffee.

Source hash: `abf56895dfb84aa1e7f3447b90f9295aa00155593408211514e0f42bf7473d1d`. Rubric hash: `00d6c55346267b60015c14b90c77dcafdb62fd0a7977bdf2478da3e710ca9d22`.

| Q1 field | Applicability | Frozen expectation | Judgment / evidence |
|---|---|---|---|
| required_activities | supported | [{"id":"s0","index":0,"sourcePhrase":"groceries","requirement":"required"}] | __________ |
| optional_activities | supported | [{"id":"s1","index":1,"sourcePhrase":"coffee","requirement":"optional"}] | __________ |
| exact_named_identity | not_applicable | Absent: invention fails | __________ |
| mandatory_order | supported | {"requiredReachability":[],"forbidAllOtherNontransitiveEdges":true,"indexBasis":"source occurrences; list position alone is not mandatory order"} | __________ |
| unordered_flexible | supported | {"mode":"unspecified","independentOccurrences":[0,1],"noFullSequenceFromList":true} | __________ |
| repeated_stops | not_applicable | Absent: invention fails | __________ |
| return_origin | not_applicable | Absent: invention fails | __________ |
| final_destination | not_applicable | Absent: invention fails | __________ |
| final_visit | not_applicable | Absent: invention fails | __________ |
| home_ambiguity | not_applicable | Absent: invention fails | __________ |
| whole_trip_limit | not_applicable | Absent: invention fails | __________ |
| travel_only_limit | not_applicable | Absent: invention fails | __________ |
| visit_durations | not_applicable | Absent: invention fails | __________ |
| duration_relations | not_applicable | Absent: invention fails | __________ |
| dates_timezones | supported | {"expressions":[],"syntheticCalendarTimezone":null,"referenceTime":"2026-11-05T15:00:00Z","resolvedDateIfKnown":null,"unknownTimezoneAction":"clarify before planning; retain expression","noInventedTimeWindow":true} | __________ |
| budget_transport | not_applicable | Absent: invention fails | __________ |
| safe_disposition | supported | {"extraction":"preserve all applicable fields","planning":"clarify unresolved required location/date/origin/identity; otherwise normal validated handoff, not a venue-availability promise","semanticClarification":[],"safeRejectionAllowedOnlyForUnsupportedOrContradictoryInstructions":false} | __________ |
| hallucinations | supported | {"forbidden":"Any mandatory activity, venue identity, edge, endpoint, date/time, duration, price, availability or capability unsupported by original source or explicit fixture context. Null/default is not permission to guess.","doNotDropUnknownActivities":true} | __________ |
| contradiction_injection | not_applicable | Absent: invention fails | __________ |
| source_provenance | supported | {"occurrenceIDs":["s0","s1"],"sourceSpanOwnership":"verbatim/bounded supported normalization and correct occurrence; borrowed or mismatched evidence fails","emptyGoldEvidence":"unspecified exact quote, never evidence optionality","explicitGoldEvidence":"retain exact asserted nonempty reference value; source grounding still required","edgeEvidence":"both referenced phrases and attached directional cue, independently proved; substring alone insufficient","requiredFields":"wire-schema required/null contract; missing property differs from explicit null"} | __________ |
| people | not_applicable | Absent: invention fails | __________ |
| geography | not_applicable | Absent: invention fails | __________ |
| shared_place | not_applicable | Absent: invention fails | __________ |
| deadline | not_applicable | Absent: invention fails | __________ |

Complete independent gold decision: __________  Date/signature: __________
Future response hash: __________  Raw24-field decision: __________  Legacy decision: __________  Guarded decision: __________
Occurrence/mapping and expected clarification checked: __________  Disagreement/unresolved notes: __________
Separate independent per-response signoff/date (only after response): __________

## 5. journey-21/r1

> Visit the pharmacy before the bank, but the bank before the pharmacy.

Source hash: `5d88d74b325fd6b2f4c3178500a842dac423cd2ed9723305f8762504eea703da`. Rubric hash: `8bda336afc89bfb4fe36e89a0b36b93a3b29bc4276f8094adcc883486cc1fffd`.

| Q1 field | Applicability | Frozen expectation | Judgment / evidence |
|---|---|---|---|
| required_activities | supported | [{"id":"s0","index":0,"sourcePhrase":"pharmacy","requirement":"required"},{"id":"s1","index":1,"sourcePhrase":"bank","requirement":"required"}] | __________ |
| optional_activities | not_applicable | Absent: invention fails | __________ |
| exact_named_identity | not_applicable | Absent: invention fails | __________ |
| mandatory_order | supported | {"requiredReachability":[],"forbidAllOtherNontransitiveEdges":true,"indexBasis":"source occurrences; list position alone is not mandatory order","sourceIntent":"contradictory; no graph may be admitted without clarification"} | __________ |
| unordered_flexible | supported | {"mode":"contradictory_not_unordered","independentOccurrences":[0,1],"noFullSequenceFromList":true} | __________ |
| repeated_stops | not_applicable | Absent: invention fails | __________ |
| return_origin | not_applicable | Absent: invention fails | __________ |
| final_destination | not_applicable | Absent: invention fails | __________ |
| final_visit | not_applicable | Absent: invention fails | __________ |
| home_ambiguity | not_applicable | Absent: invention fails | __________ |
| whole_trip_limit | not_applicable | Absent: invention fails | __________ |
| travel_only_limit | not_applicable | Absent: invention fails | __________ |
| visit_durations | not_applicable | Absent: invention fails | __________ |
| duration_relations | not_applicable | Absent: invention fails | __________ |
| dates_timezones | supported | {"expressions":[],"syntheticCalendarTimezone":null,"referenceTime":"2026-11-05T15:00:00Z","resolvedDateIfKnown":null,"unknownTimezoneAction":"clarify before planning; retain expression","noInventedTimeWindow":true} | __________ |
| budget_transport | not_applicable | Absent: invention fails | __________ |
| safe_disposition | supported | {"extraction":"preserve all applicable fields","planning":"clarify unresolved required location/date/origin/identity; otherwise normal validated handoff, not a venue-availability promise","semanticClarification":["contradictory order"],"safeRejectionAllowedOnlyForUnsupportedOrContradictoryInstructions":true} | __________ |
| hallucinations | supported | {"forbidden":"Any mandatory activity, venue identity, edge, endpoint, date/time, duration, price, availability or capability unsupported by original source or explicit fixture context. Null/default is not permission to guess.","doNotDropUnknownActivities":true} | __________ |
| contradiction_injection | supported | {"action":["contradictory order"],"mustNotExecuteToolsOrClaimBooking":true,"mustNotChooseAndDropConflictingRequirements":true} | __________ |
| source_provenance | supported | {"occurrenceIDs":["s0","s1"],"sourceSpanOwnership":"verbatim/bounded supported normalization and correct occurrence; borrowed or mismatched evidence fails","emptyGoldEvidence":"unspecified exact quote, never evidence optionality","explicitGoldEvidence":"retain exact asserted nonempty reference value; source grounding still required","edgeEvidence":"both referenced phrases and attached directional cue, independently proved; substring alone insufficient","requiredFields":"wire-schema required/null contract; missing property differs from explicit null"} | __________ |
| people | not_applicable | Absent: invention fails | __________ |
| geography | not_applicable | Absent: invention fails | __________ |
| shared_place | not_applicable | Absent: invention fails | __________ |
| deadline | not_applicable | Absent: invention fails | __________ |

Complete independent gold decision: __________  Date/signature: __________
Future response hash: __________  Raw24-field decision: __________  Legacy decision: __________  Guarded decision: __________
Occurrence/mapping and expected clarification checked: __________  Disagreement/unresolved notes: __________
Separate independent per-response signoff/date (only after response): __________

## Historical failures — preserve both

1. journey-07/r1: “Go to the pharmacy first, then the supermarket.” Model edge0→1 quoted only “first, then”. Both visits/direction were correct, but trusted evidence did not identify both stops; remain a raw provenance error and safe rejection. Independent review: __________

2. extension-repeated/r1: source is slot1 above. Original model added0→1 with “Coffee, museum, then”. Existing legacy accepted it; full review identified an invented mandatory relationship. Guard must reject0→1 and preserve supported1→2. This is an accepted critical historical failure, not rehabilitated by a future success. Independent review: __________

3. Contradictory request in slot5 must preserve both required visits/conflicting directions for rephrase. No extra occurrences, selected direction or published graph/plan. A cyclic/invalid JSON response is not a correct clarification. Clarification completeness requires review, not a keyword pass. Independent review: __________

## Additional gates

- Review all five expected absences (dates/geography/endpoints/durations/order/identity/optionality as applicable), mappings and stop protocol: __________
- Review private-state/path isolation, exact build, reservation-before-intent/send, no retries, uncertain-state recovery, review trust and original-halt preservation: __________
- No selected Q1 awaiting field; six global judgments, all66 gold and seven historical response independent signoffs remain open. Expanded/held-out qualification is separate. No model qualification granted: __________
- Current account/model/price/terms/count facts are unknown. Fresh checks require separate authorization. No financial or dispatch grant is created: __________
