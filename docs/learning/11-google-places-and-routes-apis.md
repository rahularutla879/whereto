# 11 — Google Places and Routes APIs

[Course contents](README.md) · [Glossary](GLOSSARY.md)

## Two services answer different questions

**Google Places** supplies venue identity and descriptive facts. **Google Routes** estimates travel between supplied points. Neither answers whether a cricket court has a slot or a cinema ticket is available. Where To? needs both: suitable venues without usable travel do not establish a feasible outing, while a fast route to the wrong activity is irrelevant.

[places.py](../../backend/places.py) builds searches and parses responses; [places_transport.py](../../backend/places_transport.py) owns actual HTTP. [venue_normalization.py](../../backend/venue_normalization.py) converts provider-specific records into [VenueFacts](../../backend/venue_models.py). **Normalization** creates a consistent internal shape; it does not upgrade unknown values into verified facts. [venue_quality.py](../../backend/venue_quality.py) checks relevance; [venue_geography.py](../../backend/venue_geography.py) checks supported destination evidence. Deduplication combines activity relevance around one Place ID rather than manufacturing multiple physical venues.

**Text Search** submits a text query and optional geographic bias/restriction. A **field mask** lists requested response fields. Developers use masks to bound returned data and avoid unnecessary billing tiers. The current approved profile may request Enterprise search fields for hours/ratings; minimal fields and optional gates still matter. A **Place ID** identifies Google's venue record. It is not a user authorization token.

`sequential_discovery.initialize` supports the website's location-first searches. `DiscoveryInventory` tracks retained relevant venues and untried discovery work. Explicit discovery can advance pages/strategies/areas; there is no infinite background city scan. Manual origin lookup is another Text Search through `starting_places`, not a new Geocoding integration. The owner must confirm one returned match.

## Directed route evidence

A **matrix** holds travel for origins crossed with destinations: two origins times three destinations is six billable elements, even when one HTTP request carries them. Direction matters: A→B can differ from B→A. [routes.py](../../backend/routes.py) defines route points, requests, parsing and `GoogleRouteCalculator`; [routes_transport.py](../../backend/routes_transport.py) sends the validated request.

Actual transport excerpt:

```python
session.mount("https://", requests.adapters.HTTPAdapter(max_retries=0))
```

```python
dispatch("matrix", len(body['origins']) * len(body['destinations']),
         sku='matrix_pro_element' if body['travelMode']=='DRIVE' else 'matrix_element')
```

The first line installs an HTTP adapter with no automatic retries. In the second excerpt, line 1 records the full Cartesian element count before the send; line 2 selects the existing driving Pro or walking/legacy Essentials accounting key. Input is an already validated matrix body. Output is an admitted/recorded attempt or an accounting error. Only after admission does the transport POST to Google. A timeout or invalid response does not erase the attempt or trigger a retry.

Driving uses `TRAFFIC_AWARE`, not `TRAFFIC_AWARE_OPTIMAL`; walking retains its own policy. `_validate_basic_body` reconstructs the minimal allowed body and rejects extra premium/unsupported inputs. No requested outing departure timestamp is sent as a future-traffic promise. Current route observations are evidence, not guaranteed future travel or parity with the consumer Maps application.

## Authentication and privacy

**Authentication** proves which service principal is calling Google. **Authorization** checks what that principal may do. The approved local integration uses impersonated **ADC**, Application Default Credentials, for a dedicated service account, rather than a browser API key. **OAuth** supplies short-lived access tokens. The reusable source credential remains private outside Git. Code obtains tokens server-side; the handbook never requires displaying them.

Before authentication or transport, local environment gates and provider budgets must permit access. A startup profile on the owner's machine can enable approved local features; fresh clones default to mock. Do not copy secret profiles or flip gates merely to try a lesson. Starting coordinates are explicit transient inputs, excluded from public request dumps and durable saves. Google may receive authorized points to calculate routes; “not persisted” does not mean “never processed.”

## Failure, reuse and presentation

Route evidence includes mode, observation time, status and nullable seconds/meters. `current_evidence` requires the same mode and age `0 <= age < 300` seconds; future-dated evidence is invalid. Same-location handling must be validated rather than guessed from equal display names. Missing route evidence stays missing and can prevent confirmation.

Provider errors are classified in `provider_errors.py` and `failures.py`: remote quota, local rate/admission, authentication, permission, timeout, invalid response and service failure are distinct. Safe diagnostics/correlation IDs help locate boundaries without printing provider bodies or private points.

[venue_details.py](../../backend/venue_details.py) loads scoped contact details; [saved_refresh.py](../../backend/saved_refresh.py) refreshes current details for the saved selection. Pro saved detail loading, optional Enterprise contacts and hours have separate field purposes and gates. Attribution and official Maps links remain visible; provider evidence is not silently relabeled as the app's own verification. Historical rates in the local cost ledger are estimates, not current price advice or invoices.

## Five key takeaways

1. Places discovers venues; Routes supplies travel evidence.
2. Matrix cost counts cells rather than HTTP requests alone.
3. Mode and direction belong to route identity.
4. Credentials stay in backend-controlled configuration.
5. Unknown availability cannot become a booking claim.

## Check your understanding

11.Q1. How many elements are 3 origins by 4 destinations?
11.Q2. What does a field mask select?
11.Q3. Why is A→B not enough for a return?
11.Q4. What does ADC mean?
11.Q5. When does current route evidence expire?

## Code-reading exercise — 11.R

Read routes_transport.compute_matrix and find authentication, accounting, HTTP send and error handling in order.

## Practical exercise — 11.P

Draw a fictional two-by-two matrix and count all cells including diagonals. Use no Maps requests.

See [separate answers and guidance](EXERCISE_SOLUTIONS.md#chapter-11).

[Previous chapter](10-planning-algorithms-filtering-scheduling-and-ranking.md) · [Contents](README.md) · [Next chapter](12-postgresql-supabase-sessions-and-saved-plans.md)
