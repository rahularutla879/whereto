# Complex outing interpretation — Task 50A

This is semantic understanding only. Destination identity verification, route-aware
sequencing/returns, total-time feasibility and persistence integration remain
future Tasks 50B–50E. No Google operation, database table or migration is added.

## Existing pipeline retained

The local `qwen3:4b` provider, temperature zero, thinking disabled, 8192-token
context, bounded 1024-token response, ten-minute keep-alive and owner-local one-shot
warmup remain. The existing extra-forbid Pydantic contract, duplicate-key rejection,
verbatim activity checks, canonical registry/open activities, retail policy,
manual precedence, destination calendars, deterministic follow-ups and Driving/
Walking/Strict/Flexible travel controls remain the only interpretation pipeline.

Previously `activities` encoded a linear occurrence list. Travel caps described
travel only; dates/windows described the outing calendar. None represented exact
establishments, optional stops, partial order, endpoints or whole-journey budgets.

## Additive transient contract

`Interpretation.journey` is optional for legacy callers. Current Ollama generation
requires it and visits every journey/stop constraint field explicitly, including
nullable durations/endpoints. Python-only clock/conflict fields are excluded from
the model projection. Legacy requests without advanced wording continue using their existing required activity-list semantics.

| Field | Meaning and default |
| --- | --- |
| `stops` | One entry per `activities` occurrence, in original source order. Repeats remain distinct; source order is not an optimization instruction. |
| Stop `source` | Original verbatim destination/activity phrase. No provider identity or coordinates. |
| Stop `kind` | `activity` (default): discover any suitable venue; `brand`: retain brand, allow branches; `named_place`: one specific establishment/qualified branch. |
| Stop `requirement` | `required` by default for ordinary outing requests; `optional` only with explicit source evidence. |
| Stop `evidence` | Original clause preserving optional/required/qualitative wording; absent evidence is empty, never a guessed fact. |
| Stop `duration` | Optional typed dwell duration, distinct from travel. |
| `order` | Directed `before` → `after` zero-based occurrence indexes with source clauses. Empty by default; malformed references are rejected and conflicting graphs are blocked. |
| `ordering` | `unspecified` default; `constrained` for explicit edges; `flexible` for explicit any-order wording. Omitted mode with supplied edges normalizes to constrained; inconsistent modes/cycles set the derived conflict flag and cannot execute. |
| `endpoint` | Required endpoint when present: `origin`, unresolved `home`, exact `named_place`, generic `activity`, or `brand`, plus original wording. Not an extra activity stop. |
| `total_duration` | Whole journey elapsed duration, including intended return, separate from all travel-only fields. |
| `deadline` | Original absolute deadline clause, `by`/`before`, deterministic local clock minute. No invented start. |
| `shared_place` | Same-mall requirement for specified stop indexes and original wording; distinct from a single mall-with-brands intent. |
| `order_conflict` | Python-derived cycle/mode inconsistency flag. Never supplied by Qwen; forces clarification and no planning request. |
| `clarification` | Verbatim conflicting/ambiguous clause, empty when absent. It never substitutes for a resolved constraint. |

Duration objects retain nonnegative integer `minutes`, `relation` (`exact`, `minimum`,
`maximum`, `under`, `approximate`) and original `source`. Natural hour/minute words
are checked independently. “Quick coffee” retains wording without manufactured
minutes. Bounds prevent unbounded arrays/text or numeric coercion.

For blocked advanced requests, response `context` reuses the existing destination,
calendar date/timezone, transport, first-stop Strict/Flexible preference,
between-stop preference and geography types, plus transient original origin text
and validation issues. Manual preferences retain their existing precedence. It
contains no coordinates or guessed start time. Original date/clock phrases stay
in `date_expressions`/`time_expressions`; deadline clock wording is kept only in
its deadline field. An unknown timezone reference is not verified destination-local
time. “Tomorrow afternoon” keeps tomorrow's date while the existing time-window
clarification policy remains; no afternoon clock range is invented.

## Named places and retail

SUNY College of Optometry is an exact destination. Grocery shopping is a
venue-backed activity. Walmart on Route 440 is a specific qualified branch.
Zara/Nike can identify brands without identifying one branch. Existing outlet/store
format preferences and mandatory “only” constraints remain in the original retail
intent. Same-mall containment retains the existing retail evidence contract.
Neither an exact-place reference nor a prescription request proves availability,
inventory, a tenant relationship or opening hours. No substitution is authorized.

## Validation and execution boundary

The source checks verify stop membership/order/count, verbatim provenance, numeric
values/relations, duration association, endpoint wording and bounded explicit
omissions. They reject invented endpoints, downgraded obvious exact references,
wrong duration scope, swapped durations, omitted known errands, missing returns/deadlines/optionality,
malformed references and common contradictory ordering. Cyclic/conflicting
interpretations retain their source/edges with a derived conflict flag and are
rejected at the planning boundary, allowing an honest clarification. They are conservative
checks, not a replacement keyword interpreter or a guarantee for arbitrary prose.
Unknown or unreliable language asks the user to edit. JSON validity alone is
insufficient. Narrow repairs normalize only AI-supplied verbatim references:
original capitalization, a final home phrase mistakenly repeated as an activity,
bare endpoint names with an exact final-destination clause, a generic category
mislabelled as a brand, and an omitted duration relation with explicit source
wording. After valid AI stop extraction, bounded raw-duration normalization also
recovers explicit whole-trip budgets and uniquely associated dwell lengths. It
masks existing travel-only scopes, checks numeric values/relations and refuses
ambiguous assignments, negative/oversized amounts and conflicting supplied values.
It never runs as a fallback for unavailable or invalid AI output. No stop, numeric
amount, identity, coordinate or availability is guessed.

An unresolved home endpoint asks the user to identify it or explicitly say return
to the starting point. Device/manual origin does not establish home. Mixed leg
modes or conflicting order require clarification without choosing one silently.
The complete valid extraction remains in the transient response; no precise home
location or raw prompt is added to persistent storage.

Exact destinations, bare brands lacking the existing identity-verification path,
optional stops, explicit flexible/partial/reverse order, same-mall store visits,
endpoints, whole-journey budgets/deadlines and dwell times cannot enter the ordinary
planner. The response has no planning request/cards and gives one concise
explanation. Existing simple source-order sequences continue through the existing
linear planner; ranking weights are unchanged. Unsupported capability is not
presented as a missing date/activity follow-up. Original textarea and preferences
stay editable. Ordinary activity-list follow-up corrections keep their own source
answer alongside the original extraction; they cannot erase advanced requirements. The frontend also refuses a nonempty unsupported response even if a
stale request object accompanies it.

Future consumers must enforce every required stop, each edge, endpoint and timing
relation together. Task 50B must verify exact identity and never silently substitute;
50C must handle ordering/return routes; 50D must combine verified travel and dwell
with budgets/deadlines; 50E must separately design integration/persistence. The new
semantic object is deliberately absent from ordinary planner and saved-plan DTOs
until those capabilities exist. Posting unknown advanced fields directly to the
extra-forbid planning DTO remains invalid.

## Reproduce offline verification

From `/Users/rahularutla/Documents/whereto`:

```sh
backend/.venv/bin/python -m unittest backend.test_journey -v
npm run test:backend
npm test
npm run typecheck
npm run lint
npm run build
backend/.venv/bin/python -m pip check
npm ls --depth=0
python3 scripts/security-scan.py
```

`backend/journey_fixtures.py` contains 25 explicitly invented provider replies,
never production parsing logic. `backend/.venv/bin/python -m backend.real_fixture_server --journey --port 8050`
uses them for browser checks and rejects actual provider transports. Requests not
in that explicit fixture set are refused. Ordinary production AI errors retain
safe failure and never use these fixtures as a fallback.

The opt-in actual-model runner sends only the fixed public examples to the installed
model, blocks Google transports and records semantic checks plus numeric timings:

```sh
backend/.venv/bin/python -u -m backend.ai.smoke_journey
# Focused checks/repeats; no extra call during ordinary follow-up handling:
backend/.venv/bin/python -u -m backend.ai.smoke_journey --case 1 --case 15 --repeat 2
```

Final offline acceptance: 726 backend tests reported, 692 passed and 34 opt-in
skips; frontend 236/236. TypeScript, ESLint, production build, dependency checks,
production npm audit and secret scan pass. Actual-model evidence covers all 25
scenarios across a 22/25 full batch and 4/4 final focused confirmations. The
[evaluation record](../backend/evaluation/results-task50a.json) distinguishes each
run and the combined latest per-case result. Some cases overlap few-shot examples;
this is bounded evidence, not arbitrary-language accuracy.

Matched warm latency increased from median 3.911 seconds (five pre-change warm
observations) to 9.325 seconds (six prepared post-change observations, range
6.825–25.545). One preparation call took 8.977 seconds; the first pre-change call
was 13.154 seconds with uncontrolled load state. No forced cold-model unload or
peak-memory comparison was performed. Larger structured output adds generation
work; model/context/output bounds and one-call production behavior remain.
Desktop/mobile fixture verification, cleanup and limits are recorded in HANDOVER.md.
