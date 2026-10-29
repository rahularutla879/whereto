# Local exploration limits audit — October 28, 2026

This Task 46 pass changes local application policy, not Google billing or quotas. All implementation tests use invented data. Historical checkpoints in other documents describe earlier policies.

## Verified Cloud configuration

Read-only Service Usage administration for `where-to-512422` at 21:18 UTC confirmed Text Search **200/day, 10/minute**, Compute Route Matrix **2,000 elements/day, 150/minute**, and Details **40/day, 10/minute**. No override was modified. Monitoring also recorded `ComputeRouteMatrixCellsPerMinutePerProject` exceeded at 17:46 UTC on October 28. That proves a provider minute rejection occurred; it does not identify every historical frontend failure or establish current remaining quota. Published Routes default 3,000/minute does **not** supersede the project's custom 150/minute limit.

## Audit and disposition

| Boundary | Value and enforcement | Kind / purpose | Decision |
|---|---|---|---|
| Explicit local real/exploration gates | `provider_budget.py`, `development_boundary.py`; real + REAL_DEV + explicit development + EXPLORATION_DEV, hosted environments refused | Authorization/security | Retain; exploration never activates Google by itself |
| Searches, attempts, elements per outing | Normal: 10 searches, 30 attempts, 300 elements; `ProviderSettings`/`OutingBudget` | Application cost ceilings | Already uncapped in exploration; retain normal behavior |
| Process attempts/elements | Normal 50 / 1,500, `ProviderBudget` | Application lifetime ceilings | Already uncapped in exploration; retain normal behavior |
| Manual lookup process lifetime | Normal 10; `OutingBudget._reserve_batch` | Application cost ceiling | Remove in exploration only; searches still consume real minute quota and ledger |
| Relevant inventory | 100 per distinct activity; `discovery_inventory.py` | Product target / bounded transient content | Retain independently per activity, including custom intents; never requires 100 before initial cards |
| Initial discovery | One useful search per activity, multiple later-stop anchors; adaptive refill finite | Application responsiveness | Retain |
| Explicit discovery action | At most two searches/pages; `sequential_discovery.expand` | Finite execution | Retain; explicit click required, no background loop |
| Search frontier | Initial/alternative/mixed queries, provider pages; 32 spatial strategies/activity, radius heuristic max 50 km | Finite coverage/computation | Retain; not proof of city-wide exhaustion, hard geography still applies |
| Places page size | Planner requests 10, provider maximum 20; `places.py` | Provider request shape / finite batch | Retain; pagination counts as another request |
| Route action | At most two stages of 64 new cells; `real_planning.py`, `routing_expansion.py` | Finite execution | Retain; stop earlier when useful options exist |
| Route frontier | 20 / 12 / 10 candidates per position for 2 / 3 / 4 stops; `routing_shortlist.py` | Computation, independent of 100 retained/activity | Retain and advance frontier across explicit actions |
| Beam | 96 partial paths; `spatial_beam.py` | Bounded computation / multi-path diversity | Retain; no full 100×100 route product |
| Matrix request dimensions | At most 625 cells and 50 Place-ID waypoints; `routes.py` | Documented provider request shape | Retain; app's smaller finite stages still apply |
| Rolling search/details limits | 10 requests/minute/category; process search window and shared ledger | Mirrored verified project throughput | Retain; no quota bypass |
| Rolling matrix limit | 150 cells/minute; process window + shared persistent ledger | Mirrored verified project throughput | Retain: independently verified, not an unjustifiably lower cap |
| Cross-process minute accounting | Atomic ledger reservation, short file lock; `development_cost.py` | Accounting/throughput correctness | Retain. Process and shared counters measure the same work independently; capacity is their minimum, not their sum |
| Route pre-dispatch wait | Up to 15 seconds per stage (previously 2), `provider_work.py` | Bounded admission scheduling | Cancellable; only waits for unsent capacity, never retries a failed request. Up to 30 seconds across two stages; no indefinite queue |
| Concurrency/retries | One active provider batch/process; zero provider retries | Burst control / cost / correctness | Retain. Shared ledger protects reservations across local processes; it does not globally serialize network I/O |
| Contacts | Six/outing, explicit on-demand gate and session reuse | Finite enrichment / separate owner opt-in | Retain; no new tier or live calls |
| Estimated daily cost | `DevelopmentCost.reserve`; prior $10 local-day hard block | Application estimated-cost policy | **Warning only** in authorized exploration; persistent accounting/integrity unchanged. Hard guard utility remains available outside exploration; normal request ceilings unchanged |
| Warning threshold | `WHERETO_DEV_WARN_USD=10` | Nonblocking developer information | Configurable, does not reject requests above threshold; estimated dollars are not verified Cloud billing |
| Ledger integrity/lock | Private owner file 0600, schema/cost consistency, flock max 2 seconds | Security/accounting correctness | Retain fail-closed behavior; do not reset/delete ledger. Reservations charged before I/O, uncertain/unsent failures remain conservatively charged |
| Continuation/contact state | 10 minutes, 20 active contexts, per-context action lock | Provider retention/security/no-repeat correctness | Retain. Browser pages remain browsable; generation after expiry needs a new session and cannot promise old no-repeat history |
| Browser/proxy deadlines | Interpretation 75 seconds browser; generation 120 seconds browser / 115 seconds proxy; provider connect/read 5/15 seconds | Finite execution/cancellation | Retain AbortSignal and cooperative disconnect cancellation. Already sent operations cannot be recalled or refunded |

The local 150-cell message came from the minimum of process/shared-ledger capacity; the daily message came from durable reservation exceeding the configured estimated cap. Removing accounting or assuming Google's published default would be unsafe and unnecessary. Exploration now passes `enforce_limit=False` only after centralized local-real configuration validation. `WHERETO_DEV_DAILY_USD` remains the hard-guard utility setting; `WHERETO_DEV_WARN_USD` is the exploration warning. Other normal-mode lifetime ceilings remain as before; normal mode does not newly instantiate a persistent ledger.

## Operational consequences

The ledger retains per-SKU reservations, actual dispatch counts and gross estimates across outings and restarts. Above the warning threshold the developer panel explicitly says nonblocking; no remaining spending allowance is claimed. Corrupt, unsafe or unavailable accounting still refuses unsent work. No provider content, request IDs, tokens or personal coordinates are stored in it.

Existing estimates remain $0.032 Pro search, $0.035 optional ratings search, $0.020 Details and $0.005/route element. These are documented gross assumptions, not a fresh price quotation or verified charge; allowances, credits and unrelated Cloud use are excluded. Exploration can now exceed $10/day. The approximately $40–$50/month target and $25/$45/$50 alerts are **not hard caps**. Quotas may stop work earlier, and alerts can lag. No automatic retry, cost-ledger reset, Cloud quota or billing change is part of this pass.

Temporary route admission preserves candidate pools/frontiers, known routes and saved pages. Known travel violations can be shown in explicitly separated alternatives; missing evidence remains unverified. A temporary rate restriction is never evidence that suitable venues do not exist. Previous/Next makes no provider requests.
