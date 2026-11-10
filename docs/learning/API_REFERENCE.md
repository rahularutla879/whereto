# Current API reference

**Do not send the sample POSTs just to study them.** On the owner's real local profile, planning, lookup, details and saved refresh can call paid providers. These are contracts verified by source/AST, not fresh endpoint executions.

HTTP = Hypertext Transfer Protocol. JSON = JavaScript Object Notation. GET reads metadata; POST submits an action/body. A 200 may contain clarification or no results. The browser normally calls Next.js; FastAPI owns validation/planning. All paths below are current code, not proposed cloud endpoints.

## Endpoint inventory

| Browser Next.js path / method | FastAPI path / function in main.py | Input | Output / important constraints |
|---|---|---|---|
| GET `/api/health` | GET `/health`, health | None | Backend `{status:"ok"}`; proxy `{status:"ok",backend:"ok"}` or 503 unavailable. Does not exercise AI/Maps/SQL. |
| GET `/api/planning-mode` | Same path, planning_mode | None | mode, enabled, explorationEnabled, startingLookupEnabled, contactDetailsEnabled. Mode metadata only. |
| POST `/api/interpret` | Same path, interpret_endpoint → interpret_outing | InterpretationInput | InterpretationResult: interpretation, nullable request, notes/issues/questions/pending/context, optional advancedToken and executionStatus. Shape-valid output is not planning authority. |
| POST `/api/plans/generate` | Same path, generate_endpoint → generate_plan | PlannerInput inheriting PlanningRequest | RankingResult; date and beginning rechecked, mock/real dispatch; server save receipt may be issued. |
| POST `/api/plans/options` | Same path, options_endpoint → more_options | OptionsRequest | RankingResult family with continuation; opaque session membership/expiry; different options versus explicit expandDiscovery. |
| POST `/api/plans/advanced` | Same path, advanced_endpoint | AdvancedInput | AdvancedResult status clarification/results/no_results/unsupported/provider_failure, options/questions/token; gated local sessions only. |
| POST `/api/starting-places` | Same path, starting_places | StartingPlaceQuery | Bounded matches with IDs, names, addresses, coordinates, precision and attribution; separate explicit confirmation required. Local lookup gate. |
| POST `/api/starting-areas` | Same path, starting_areas | StartingAreaQuery | Verified bounded public suggestions/matches and reference context or no-match message; compatibility endpoint, not ordinary Surprise Me behavior. |
| POST `/api/venues/details` | Same path, venue_details | ContactRequest | Scoped current contact/detail result for allowed place/token; local gate and budgets, not arbitrary ID access. |
| POST `/api/plans/save` | Same path, save_endpoint → save | SaveRequest | `{saved:true}` after atomic restricted SQL transaction; the generated result already supplied the access token; no provider call by save itself. |
| POST `/api/plans/reopen` | Same path, reopen_endpoint → reopen | OpenRequest | SavedDocument plus expiry/selection and policy flags automaticVenueDetails/hoursRefreshAvailable; read is distinct from refresh. |
| POST `/api/plans/refresh` | Same path, refresh_saved_plan | RefreshRequest | candidateId, per-reference venues result/status and diagnostics; selected real option only, bounded one-action replay metadata. |
| GET `/api/development-diagnostics` | Same path, development_diagnostics | None | Protected local aggregates if enabled; otherwise 404. No raw body/credentials/origin archive. |

Sources: [all FastAPI routes](../../backend/main.py), [Next API directory](../../app/api), [provider proxy](../../lib/provider-proxy.ts), [persistence proxy](../../lib/persistence-proxy.ts), [local diagnostics guard](../../lib/development-access.ts). There are 13 explicit FastAPI routes and 13 matching Next API route files; `/api/health` intentionally maps to `/health`.

## Request examples: structure, not authorization

Interpretation body:

```json
{"text":"Dinner and drinks in Sydney today.","preferences":{}}
```

A pending clarification resubmits matching `text`, the returned `pending` structure and typed `answers` such as `{"date":"tomorrow"}`. The backend revalidates it. Follow-ups do not automatically invoke another model; stale or unrelated state is not trusted. Do not manually paste private pending data into shared reports.

Ordinary generation uses the validated `request` plus accepted origin context from the client. Activities are normalized categories (dinner → food) or grounded supported custom intents, not arbitrary Google IDs. A real confirmed startingLocation carries point/explicitly_authorized/source data; a raw typed origin label is not confirmation. Surprise mode excludes an origin-to-first route and cannot satisfy an explicit return-to-origin journey.

Options and advanced bodies below show public field **shapes**; placeholders are deliberately invalid credentials and must not be sent:

```json
{"token":"<returned-options-token>","expandDiscovery":false,"showBeyond":false}
```

```json
{"token":"<returned-advanced-token>","dwell":{"occurrence":1,"minutes":20,"relation":"exact"}}
```

```json
{"receipt":"<server-save-receipt>","accessToken":"<private-access-token>","candidateIds":["<server-candidate-id>"],"selectedId":"<server-candidate-id>"}
```

Save/open/advanced Token fields use exactly 43 URL-safe characters matching `[A-Za-z0-9_-]`, generated from 32 random bytes. Options/ContactRequest token fields have their own bounded string declaration; do not confuse structural length with valid membership. All capability operations require server-side scope/membership/expiry too. Never put private tokens in diagnostic examples.

## Responses and failures

`RankingResult` separates plans, provisionalPlans, explorationPlans/alternativeBatches, errors, rejectionReasons, notes and scoped tokens. `adaptRanking` rejects malformed upstream structure, mixed provider/mode identity and duplicate assignments. Known violations are normally excluded; explicit scoped beyond-limit alternatives are labeled. `AdvancedResult` has at most three options and may instead ask questions. Feasible means checked evidence fits applicable constraints, not booked availability.

Main failure shape commonly includes `code`, `message`, `correlationId`, `diagnostics`, sometimes continuation. Not all proxy/boundary failures share that shape. Use status **and** code; protected proxies can sanitize/map unfamiliar upstream failures. Production browser payload filtering removes internal diagnostics, not server accounting.

| Status | Examples / boundary |
|---|---|
| 400 | Unparseable JSON at interpret/generate Next routes |
| 403 | Nonlocal/cross-origin private boundary |
| 408 | Managed body read exceeds five seconds |
| 409 | Canonical duplicate in-flight, stale save reference or other scoped conflict |
| 413 | Body too large; protected actions 4096 bytes |
| 422 | Pydantic/semantic invalid request, invalid answer, destination/origin/date refusal |
| 429 | request_burst_limited, provider_local_rate_limit, provider_quota_rejected |
| 500 | internal_application_error |
| 503 | llm_unavailable/timeout/invalid_response, backend_unavailable, service_busy, provider service/admission, database unavailable |

`RequestManagement` bounds most other managed bodies to 65536 bytes and all managed body reads to five seconds. `persistenceProxy` is same-origin loopback only, checks JSON object shape, bounds its body and uses a 45-second proxy timeout. Interpret proxy timeout is 70 seconds; generation proxy 115 seconds; browser client bounds are separate. Invalid duplicate keys/nonfinite constants are specifically rejected at protected Python JSON boundaries and strict AI decoding; do not claim every generic JSON parser has that behavior.

## Exact current request declarations

The tables below preserve actual annotated types/defaults, including nullable and optional legacy fields. `Field(...)` means required. A `default_factory` constructs a fresh value. `strict=True` disallows inappropriate coercion; `ge`/`le` mean greater/equal and less/equal, `gt`/`lt` are strict bounds. `exclude=True` affects serialization; `repr=False` only suppresses ordinary representation. `Annotated` attaches constraints to a type. See source validators for cross-field rules, not just field bounds.

### ManualPreferences

Source: [backend/interpretation.py](../../backend/interpretation.py); bases: `ContractModel`. Inherited fields/checks also apply. These declarations are statically extracted, not a generated live OpenAPI response.

| Field | Type | Default / bound declaration |
|---|---|---|
| `location` | <code>str</code> | <code>''</code> |
| `date` | <code>str</code> | <code>''</code> |
| `people` | <code>str</code> | <code>''</code> |
| `budget` | <code>str</code> | <code>''</code> |
| `travel` | <code>str</code> | <code>''</code> |
| `cost` | <code>CostPreference</code> | <code>CostPreference.balanced</code> |
| `costExplicit` | <code>bool</code> | <code>Field(default=False, strict=True)</code> |
| `transport` | <code>Literal['', 'driving', 'walking']</code> | <code>''</code> |

### ClarificationAnswers

Source: [backend/interpretation.py](../../backend/interpretation.py); bases: `ContractModel`. Inherited fields/checks also apply. These declarations are statically extracted, not a generated live OpenAPI response.

| Field | Type | Default / bound declaration |
|---|---|---|
| `endpoint` | <code>str</code> | <code>Field(default='', max_length=200)</code> |
| `location` | <code>str</code> | <code>Field(default='', max_length=80)</code> |
| `people` | <code>str</code> | <code>Field(default='', max_length=80)</code> |
| `date` | <code>str</code> | <code>Field(default='', max_length=100)</code> |
| `activities` | <code>str</code> | <code>Field(default='', max_length=500)</code> |
| `time` | <code>str</code> | <code>Field(default='', max_length=150)</code> |

### PendingClarification

Source: [backend/interpretation.py](../../backend/interpretation.py); bases: `ContractModel`. Inherited fields/checks also apply. These declarations are statically extracted, not a generated live OpenAPI response.

| Field | Type | Default / bound declaration |
|---|---|---|
| `text` | <code>Annotated[str, Field(min_length=1, max_length=4000)]</code> | <code>**required**</code> |
| `interpretation` | <code>Interpretation</code> | <code>**required**</code> |
| `answers` | <code>ClarificationAnswers</code> | <code>Field(default_factory=ClarificationAnswers)</code> |
| `referenceTime` | <code>AwareDatetime</code> | <code>**required**</code> |

### InterpretationInput

Source: [backend/interpretation.py](../../backend/interpretation.py); bases: `ContractModel`. Inherited fields/checks also apply. These declarations are statically extracted, not a generated live OpenAPI response.

| Field | Type | Default / bound declaration |
|---|---|---|
| `text` | <code>Annotated[str, Field(min_length=1, max_length=4000)]</code> | <code>**required**</code> |
| `preferences` | <code>ManualPreferences</code> | <code>Field(default_factory=ManualPreferences)</code> |
| `calendarTimezone` | <code>str &#124; None</code> | <code>Field(default=None, max_length=100)</code> |
| `hasCurrentLocation` | <code>bool</code> | <code>Field(default=False, strict=True)</code> |
| `pending` | <code>PendingClarification &#124; None</code> | <code>None</code> |
| `answers` | <code>ClarificationAnswers</code> | <code>Field(default_factory=ClarificationAnswers)</code> |

### OutingRequest

Source: [backend/models.py](../../backend/models.py); bases: `ContractModel`. Inherited fields/checks also apply. These declarations are statically extracted, not a generated live OpenAPI response.

| Field | Type | Default / bound declaration |
|---|---|---|
| `activities` | <code>list[ActivityType]</code> | <code>Field(min_length=1, max_length=4)</code> |
| `activityIntents` | <code>dict[str, Annotated[Nonblank, Field(max_length=500)]]</code> | <code>Field(default_factory=dict, max_length=4)</code> |
| `location` | <code>Location</code> | <code>'Baltimore'</code> |
| `people` | <code>GroupSize &#124; None</code> | <code>None</code> |
| `date` | <code>OutingDate &#124; None</code> | <code>None</code> |
| `budget` | <code>Annotated[Money, Field(le=100000)] &#124; None</code> | <code>None</code> |
| `travel` | <code>TravelMinutes &#124; None</code> | <code>None</code> |
| `groupBudget` | <code>Money &#124; None</code> | <code>None</code> |
| `maxLegTravel` | <code>TravelMinutes &#124; None</code> | <code>None</code> |
| `firstTravel` | <code>FirstTravel &#124; None</code> | <code>None</code> |
| `betweenTravel` | <code>FirstTravel &#124; None</code> | <code>None</code> |
| `planningMode` | <code>Literal['origin', 'surprise']</code> | <code>'origin'</code> |
| `calendarTimezone` | <code>str &#124; None</code> | <code>Field(default=None, max_length=100)</code> |
| `explicitStart` | <code>bool &#124; None</code> | <code>Field(default=None, strict=True)</code> |
| `explicitEnd` | <code>bool &#124; None</code> | <code>Field(default=None, strict=True)</code> |
| `destinationContext` | <code>DestinationContext &#124; None</code> | <code>None</code> |
| `geography` | <code>Geography</code> | <code>Field(default_factory=Geography)</code> |
| `maxFirstLegTravel` | <code>TravelMinutes &#124; None</code> | <code>None</code> |
| `travelExclusive` | <code>bool</code> | <code>Field(default=False, strict=True)</code> |
| `maxLegTravelExclusive` | <code>bool</code> | <code>Field(default=False, strict=True)</code> |
| `maxFirstLegTravelExclusive` | <code>bool</code> | <code>Field(default=False, strict=True)</code> |
| `startTime` | <code>StartMinute</code> | <code>600</code> |
| `endTime` | <code>EndMinute</code> | <code>1440</code> |
| `requireAvailability` | <code>bool</code> | <code>Field(default=False, strict=True)</code> |
| `requireWheelchairAccess` | <code>bool</code> | <code>Field(default=False, strict=True)</code> |
| `cost` | <code>CostPreference</code> | <code>CostPreference.balanced</code> |
| `transport` | <code>TransportationMode &#124; None</code> | <code>None</code> |
| `dinner` | <code>bool</code> | <code>Field(default=False, strict=True)</code> |
| `dinnerStops` | <code>list[Annotated[int, Field(strict=True, ge=0, le=3)]] &#124; None</code> | <code>None</code> |
| `allowRevisits` | <code>bool</code> | <code>Field(default=False, strict=True)</code> |

### PlanningRequest

Source: [backend/models.py](../../backend/models.py); bases: `OutingRequest`. Inherited fields/checks also apply. These declarations are statically extracted, not a generated live OpenAPI response.

| Field | Type | Default / bound declaration |
|---|---|---|
| `date` | <code>OutingDate</code> | <code>Field(...)</code> |
| `transport` | <code>Literal[TransportationMode.driving, TransportationMode.walking]</code> | <code>TransportationMode.driving</code> |

### PlannerInput

Source: [backend/real_planning.py](../../backend/real_planning.py); bases: `PlanningRequest`. Inherited fields/checks also apply. These declarations are statically extracted, not a generated live OpenAPI response.

| Field | Type | Default / bound declaration |
|---|---|---|
| `recentSurpriseIds` | <code>list[PlaceID]</code> | <code>Field(default_factory=list, max_length=120, exclude=True, repr=False)</code> |
| `useOriginAsSearchAnchor` | <code>bool</code> | <code>Field(default=False, strict=True, exclude=True)</code> |
| `locationFirst` | <code>bool</code> | <code>Field(default=False, strict=True)</code> |
| `referenceToken` | <code>str &#124; None</code> | <code>Field(default=None, min_length=1, max_length=100, exclude=True, repr=False)</code> |
| `manualStartingPlace` | <code>str &#124; None</code> | <code>Field(default=None, max_length=200, exclude=True, repr=False)</code> |
| `startingLocation` | <code>AuthorizedStart &#124; None</code> | <code>Field(default=None, repr=False, exclude=True)</code> |
| `currentArea` | <code>SearchArea &#124; None</code> | <code>Field(default=None, repr=False, exclude=True)</code> |
| `searchRadius` | <code>float &#124; None</code> | <code>Field(default=None, gt=0, le=50000, strict=True, allow_inf_nan=False)</code> |
| `maxFirstLegTravel` | <code>int &#124; None</code> | <code>Field(default=None, ge=0, le=1440, strict=True)</code> |

### OptionsRequest

Source: [backend/main.py](../../backend/main.py); bases: `BaseModel`. Inherited fields/checks also apply. These declarations are statically extracted, not a generated live OpenAPI response.

| Field | Type | Default / bound declaration |
|---|---|---|
| `showBeyond` | <code>bool</code> | <code>Field(default=False, strict=True)</code> |
| `expandDiscovery` | <code>bool</code> | <code>Field(default=False, strict=True)</code> |
| `token` | <code>str</code> | <code>Field(min_length=1, max_length=100)</code> |

### ContactRequest

Source: [backend/main.py](../../backend/main.py); bases: `BaseModel`. Inherited fields/checks also apply. These declarations are statically extracted, not a generated live OpenAPI response.

| Field | Type | Default / bound declaration |
|---|---|---|
| `placeId` | <code>PlaceID</code> | <code>**required**</code> |
| `token` | <code>str</code> | <code>Field(min_length=1, max_length=100)</code> |

### AdvancedInput

Source: [backend/advanced_planning.py](../../backend/advanced_planning.py); bases: `ContractModel`. Inherited fields/checks also apply. These declarations are statically extracted, not a generated live OpenAPI response.

| Field | Type | Default / bound declaration |
|---|---|---|
| `token` | <code>Token</code> | <code>Field(repr=False)</code> |
| `startingLocation` | <code>AuthorizedStart &#124; None</code> | <code>Field(default=None, repr=False)</code> |
| `firstTravel` | <code>FirstTravel &#124; None</code> | <code>None</code> |
| `betweenTravel` | <code>FirstTravel &#124; None</code> | <code>None</code> |
| `edits` | <code>AdvancedEdits &#124; None</code> | <code>None</code> |
| `proceedClosed` | <code>Token &#124; None</code> | <code>Field(default=None, repr=False)</code> |
| `choice` | <code>Choice &#124; None</code> | <code>None</code> |
| `dwell` | <code>DwellAnswer &#124; None</code> | <code>None</code> |
| `departure` | <code>str &#124; None</code> | <code>Field(default=None, pattern='^([01]\\d&#124;2[0-3]):[0-5]\\d$')</code> |
| `date` | <code>str &#124; None</code> | <code>Field(default=None, min_length=1, max_length=100)</code> |
| `action` | <code>Literal['different', 'discover', 'beyond'] &#124; None</code> | <code>None</code> |
| `searchNearOrigin` | <code>bool</code> | <code>Field(default=False, strict=True)</code> |
| `includeBeyond` | <code>bool</code> | <code>Field(default=False, strict=True)</code> |
| `destination` | <code>str &#124; None</code> | <code>Field(default=None, min_length=2, max_length=200)</code> |

### DwellAnswer

Source: [backend/advanced_preferences.py](../../backend/advanced_preferences.py); bases: `ContractModel`. Inherited fields/checks also apply. These declarations are statically extracted, not a generated live OpenAPI response.

| Field | Type | Default / bound declaration |
|---|---|---|
| `occurrence` | <code>int</code> | <code>Field(strict=True, ge=0, lt=4)</code> |
| `minutes` | <code>int</code> | <code>Field(strict=True, ge=0, le=10080)</code> |
| `relation` | <code>Literal['exact', 'minimum', 'maximum', 'under', 'approximate']</code> | <code>'approximate'</code> |
| `zeroCountedTime` | <code>bool</code> | <code>Field(default=False, strict=True)</code> |

### Choice

Source: [backend/advanced_preferences.py](../../backend/advanced_preferences.py); bases: `ContractModel`. Inherited fields/checks also apply. These declarations are statically extracted, not a generated live OpenAPI response.

| Field | Type | Default / bound declaration |
|---|---|---|
| `occurrence` | <code>int</code> | <code>Field(strict=True, ge=0, le=4)</code> |
| `placeId` | <code>str</code> | <code>Field(min_length=1, max_length=200)</code> |

### AdvancedEdits

Source: [backend/advanced_preferences.py](../../backend/advanced_preferences.py); bases: `ContractModel`. Inherited fields/checks also apply. These declarations are statically extracted, not a generated live OpenAPI response.

| Field | Type | Default / bound declaration |
|---|---|---|
| `dwell` | <code>list[DwellAnswer]</code> | <code>Field(default_factory=list, max_length=4)</code> |
| `budgetScope` | <code>Literal['outing', 'travel'] &#124; None</code> | <code>None</code> |
| `resetDwell` | <code>list[Annotated[int, Field(strict=True, ge=0, lt=4)]]</code> | <code>Field(default_factory=list, max_length=4)</code> |
| `removeClosure` | <code>list[Annotated[int, Field(strict=True, ge=0, lt=4)]]</code> | <code>Field(default_factory=list, max_length=4)</code> |
| `resetDeparture` | <code>bool</code> | <code>Field(default=False, strict=True)</code> |
| `departure` | <code>str &#124; None</code> | <code>Field(default=None, pattern='^([01]\\d&#124;2[0-3]):[0-5]\\d$')</code> |
| `choices` | <code>list[Choice]</code> | <code>Field(default_factory=list, max_length=5)</code> |

### StartingPlaceQuery

Source: [backend/starting_places.py](../../backend/starting_places.py); bases: `BaseModel`. Inherited fields/checks also apply. These declarations are statically extracted, not a generated live OpenAPI response.

| Field | Type | Default / bound declaration |
|---|---|---|
| `query` | <code>str</code> | <code>Field(min_length=3, max_length=200, repr=False)</code> |

### StartingAreaQuery

Source: [backend/starting_areas.py](../../backend/starting_areas.py); bases: `BaseModel`. Inherited fields/checks also apply. These declarations are statically extracted, not a generated live OpenAPI response.

| Field | Type | Default / bound declaration |
|---|---|---|
| `destination` | <code>str</code> | <code>Field(min_length=2, max_length=80)</code> |
| `activities` | <code>list[ActivityType]</code> | <code>Field(min_length=1, max_length=4)</code> |
| `transport` | <code>str</code> | <code>Field(default='driving', pattern='^(driving&#124;walking)$')</code> |
| `firstTravel` | <code>FirstTravel &#124; None</code> | <code>None</code> |
| `maxLegTravel` | <code>int &#124; None</code> | <code>Field(default=None, ge=0, le=1440, strict=True)</code> |
| `maxLegTravelExclusive` | <code>bool</code> | <code>Field(default=False, strict=True)</code> |
| `travel` | <code>int &#124; None</code> | <code>Field(default=None, ge=0, le=1440, strict=True)</code> |
| `travelExclusive` | <code>bool</code> | <code>Field(default=False, strict=True)</code> |
| `geography` | <code>Geography</code> | <code>Field(default_factory=Geography)</code> |

### SaveRequest

Source: [backend/saved_plans.py](../../backend/saved_plans.py); bases: `ContractModel`. Inherited fields/checks also apply. These declarations are statically extracted, not a generated live OpenAPI response.

| Field | Type | Default / bound declaration |
|---|---|---|
| `receipt` | <code>Token</code> | <code>Field(repr=False)</code> |
| `accessToken` | <code>Token</code> | <code>Field(repr=False)</code> |
| `candidateIds` | <code>list[CandidateID]</code> | <code>Field(min_length=1, max_length=3)</code> |
| `selectedId` | <code>CandidateID</code> | <code>**required**</code> |

### OpenRequest

Source: [backend/saved_plans.py](../../backend/saved_plans.py); bases: `ContractModel`. Inherited fields/checks also apply. These declarations are statically extracted, not a generated live OpenAPI response.

| Field | Type | Default / bound declaration |
|---|---|---|
| `accessToken` | <code>Token</code> | <code>Field(repr=False)</code> |

### RefreshRequest

Source: [backend/saved_refresh.py](../../backend/saved_refresh.py); bases: `OpenRequest`. Inherited fields/checks also apply. These declarations are statically extracted, not a generated live OpenAPI response.

| Field | Type | Default / bound declaration |
|---|---|---|
| `refreshId` | <code>UUID</code> | <code>**required**</code> |
| `candidateId` | <code>str</code> | <code>Field(min_length=1, max_length=200)</code> |
| `includeContacts` | <code>bool</code> | <code>Field(default=False, strict=True)</code> |
| `includeHours` | <code>bool</code> | <code>Field(default=False, strict=True)</code> |

## Cross-field and membership rules the tables cannot replace

- OutingRequest validates end after start, valid timezone names, event-date needs and dinner-stop indexes; PlanningRequest requires a date and driving/walking. Calendar freshness is checked at publication.
- Manual values/answers apply through interpretation precedence; price/group budget and unsupported source requirements must not be silently relaxed. Party-size compatibility fields do not reinstate a current capacity feature.
- Journey validates occurrence references/cycles; source checks verify bounded duration/optionality/order/endpoint evidence. Known legacy ordering gaps remain; V4/V5 are not activated enforcement.
- Advanced edits forbid duplicate occurrence edits, conflicting reset/edit operations and invalid under-zero dwell. Session run additionally checks configuration, membership, original source and applicable timing.
- Starting lookup trims text, rejects control characters and requires 3–200 characters; selecting a match is separate from lookup.
- Save receipt checks server-generated candidate membership/selected ID before writing. Open checks token hash/expiry/RLS; refresh rechecks open access and only selected real option membership for every action.
- `/api/starting-areas` is an existing capability, not the default Surprise Me UI. Its source validates request compatibility again on confirmation.

[Data flows](DATA_FLOW_REFERENCE.md) · [Source index](PROJECT_FILE_MAP.md) · [Debugging](DEBUGGING_PLAYBOOK.md)
