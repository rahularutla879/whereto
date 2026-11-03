## Task 50E — explicit current traffic authorization

The consolidated owner request authorizes Driving Matrix `TRAFFIC_AWARE` and its Pro tier within existing controlled local development. Walking stays unchanged. Do not use `TRAFFIC_AWARE_OPTIMAL`, a second verification pass, extra Cartesian cells, hidden retries, or change Cloud quotas/billing/identities/private profiles. Driving gross first-tier accounting is $0.010/element; Walking/legacy Essentials remains $0.005/element. Preserve existing usage when adding the Pro ledger key. Current evidence expires after five minutes and never establishes a guaranteed future arrival or consumer Maps parity. Automated/browser Google sends stay blocked. [Implementation and checks](docs/task50e-consolidated.md). Task 51 remains unstarted.

# Safeguards

- Preserve the current visual design and working behavior unless the agreed task requires a change. Keep modifications focused; avoid unrelated edits and refactoring.
- Do not introduce paid external services, subscriptions, or billable API usage without owner approval. Check pricing and terms before committing to a provider.
- Never expose credentials in chat, logs, committed files, or browser code. Keep secret keys server-side when integrations are introduced. .gitignore already excludes .env files except .env.example; examples must contain placeholders only.
- Obtain approval before destructive actions such as deleting owner work, resetting history, or replacing data. Do not initialize Git, connect GitHub, deploy, or publish as an incidental step.
- Label fictional venues, schedules, prices, capacities, durations, and travel estimates as mock. Real integrations must identify sources and uncertainty; unknown availability or opening hours must not become invented facts.
- Do not claim AI, real routing, bookings, persistence, or other planned features exist before they are implemented. Distinguish implementation, automated test evidence, and browser verification.

## Hard planning constraints

- Honor requested activities and supported location/date, group capacity, per-person budget, and total inter-stop travel cap. Preserve activity order unless a future task explicitly changes that behavior.
- Never silently omit an activity, substitute another event/date, or relax a hard limit to produce results. Explain unsupported requests or infeasibility instead.
- Zero budget and zero travel are valid limits. Current travel excludes the trip to the first stop and the trip home; costs exclude transport, taxes, tips, booking fees, and extras. Keep these boundaries visible.
- Respect fixed event starts, stop durations, travel time, non-overlap, dinner timing, and the current midnight cutoff. Do not treat mock schedules or capacity as verified real-world feasibility.
- Cost/experience preferences rank only feasible candidates; they cannot override hard constraints. Fewer than three distinct results is acceptable.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the current implementation and [HANDOVER.md](HANDOVER.md) for evidence and limitations.


## Task 34 interpretation safeguards

- Trust AI output only after the existing strict structured contract, bounded source checks, manual precedence and deterministic date resolution produce an effective request. Unknown fields and duplicate JSON keys are rejected, including unknown critical constraints.
- Do not derive a group budget by multiplying a per-person budget, swap travel scopes, infer spending mode from a numeric cap, or silently interpret a minimum as a maximum. Unsupported currencies/distance units and recognized mandatory venue requirements require an explanation.
- Keep manual overrides and follow-up answers separate from automatic display values. Validation failures must not populate guessed controls, send partial plans or invoke the retired interpreter. Follow-ups remain deterministic and use no extra AI calls.
- Every published outing needs a valid date/window; recheck expiry at the public planning boundary. Validation establishes bounded interpretation confidence, not arbitrary-language completeness or real-world availability.


## Task 39 — external venue/travel usage lock

- `where-to-512422` has Places API (New) and Routes API enabled and **Free Trial billing linked by the owner**, a dedicated keyless local impersonation identity (no API keys/private keys), and a saved $50/month account-wide alert budget (explicitly approved because project-only selection was unavailable). Maps JavaScript remains disabled. Lower quotas are verified; exact values and remaining approval steps are in [docs/billing-safeguards.md](docs/billing-safeguards.md). Tasks 39–45 are complete; Tasks 41–42 and the initial Task 43 implementation used no live requests. The separately authorized Task 43 live-verification ledger is in docs/route-calculator.md. Task 43 adds bounded routing with unchanged ceilings and a local minute-quota admission check; Task 44 evaluates supplied evidence offline; Task 45 labels source identity and field-level uncertainty offline. Task 46 has not started. See [Task 40 usage and verification](docs/venue-discovery.md).
- Keep `VENUE_DATA_MODE` absent or `mock`; generic live provider/Routes access remains locked. Task 40 adds only a separate `WHERETO_PLACES_DEV=1` backend development discovery gate, checked before authentication and at transport. Never export/save it for ordinary startup; keep it absent after testing. The Task 40 two-request live allowance is exhausted; further live tests need separate authorization. Do not link billing, start a trial, enter payment details, accept financial terms or issue live provider requests without explicit authorization. Billing setup does not itself authorize live use.
- Future adapters must use the shared process/outing budget before every request/page/retry and enforce candidate/matrix limits before routing. No hidden SDK retries, per-itinerary network calls or silent activity omissions. Mock planning and local AI behavior retain their existing rules.
- Current local ADC targets the dedicated service account with only `serviceusage.services.use`; owner impersonation is scoped to that account. Its reusable source user refresh credential must remain protected outside Git (ADC mode 0600). The shared OAuth `cloud-platform` scope is not a two-API allowlist; do not broaden IAM or provider access incidentally. Future credentials must be backend-only and limited to necessary APIs/access. API keys require verified public egress IP restrictions and an approved untracked secret location; an OAuth service identity requires separately verified minimal permissions and short-lived token handling. No invented local/host IP, unrestricted key, `NEXT_PUBLIC_*` key, browser key or committed secret. Defer credentials while appropriate restrictions cannot be established.
- Quotas, free allowances and process-local limits do not guarantee a hard monthly spending ceiling. Saved $50 actual-cost alerts at 50%, 90%, 100% ($25/$45/$50) exclude credits, may lag usage and are notifications only. The budget covers all projects linked to the account, currently only Where To. The trial is not authorized for paid upgrade. Proposed quota/application increases are not approved or applied. Reverify quotas, budget recipients and credential restrictions after financial setup and before any approved live use.


## Task 43 — isolated route calculation

- The generic live-provider lock remains unconditional. A separate backend-only `WHERETO_ROUTES_DEV=1` gate permits only a future separately authorized local Routes verification; it must remain absent for ordinary startup and is checked before authentication/transport. The initial Task 43 implementation was offline; later live verification requires its own bounded authorization and ledger. Do not reuse the exhausted Task 40 Places allowance. See [route calculator safeguards](docs/route-calculator.md).
- Admit the full required adjacent-group matrix plan before I/O, including any explicitly authorized start. Preserve 27 elements/outing, session/request limits, concurrency 1 and retries 0. Count every origins × destinations cell, retain conservative reservations on failure, and respect the existing cloud 300/day and 60/minute ceilings. Never split work to evade limits or infer a starting point from a destination name.


## October 24, 2026 — owner-approved API spending policy

- Development API spending of approximately **$40–$50 USD/month** is a planning target. Reasonable, controlled spending for authorized development/testing is acceptable; there is no blanket zero-spend rule. This target does not authorize uncontrolled requests or unbounded recurring use.
- Continue within an already authorized test without repeatedly seeking approval for trivial costs inside its request/element allowance. Monitor request/element usage and estimated versus posted costs; respect existing $50 account-wide alerts, quotas, budgets, concurrency and zero-retry safeguards. Prefer efficient batching and caching only where provider terms permit. Avoid unnecessary expensive fields/premium features.
- Keep the Google Cloud Free Trial; do not upgrade the billing plan without explicit approval. Major quota increases, substantial recurring costs and billing-plan changes need separate approval. No new quotas, alert amounts or application ceilings are approved by this spending target.
- Task 43 verification authorization (**now consumed: one request/four elements, HTTP 200; live gate disabled afterward**): **one driving Compute Route Matrix request, at most four elements**, explicitly including A→A, A→B, B→A and B→B. Use existing keyless OAuth, Essentials features/minimal mask, no retries or additional provider calls, no Places discovery, and disable the development routing gate immediately afterward. Record the consumed allowance in the route verification ledger; a completed/failed attempt is not reusable authorization. Stop before Task 44.


## October 25, 2026 — Task 46 authorization and local integration

The owner's explicit Task 46 request supersedes the earlier mock-only generic lock **only** for deliberate local real planning with `VENUE_DATA_MODE=real` plus `WHERETO_REAL_DEV=1`. Mock remains default. Production/known hosting environments refuse real mode. No deployment, billing upgrade, quota increase or ongoing automated Google use is authorized. Existing isolated development switches are not ordinary startup instructions.

Task 46 live verification is capped across the entire task at **four Places Text Search requests and 27 billable Route Matrix elements**, zero retries, zero Enterprise search fields, zero Place Details/other billable methods. Count attempts conservatively and never reset counters to evade the allowance. The contact feature uses mocked Details responses for verification and has a separate default-off gate, `WHERETO_CONTACT_DETAILS_DEV=1`. A future live Details check needs separate authorization.

The existing $40–$50 target, Free Trial, $50 account-wide alerts, lower Cloud quotas, four searches, three candidates/activity, 27 elements/outing, 20 attempts/outing, 50 attempts/process and concurrency one stay unchanged. Six contact requests/outing are a sublimit inside existing totals. Starting coordinates remain transient/excluded from results and diagnostics; no device prompt on page open. Never infer a start from a destination, loosen travel caps or label unknown prices as a passed financial constraint. [Current flow and verification](docs/real-planning.md). Stop after Task 46; Task 47 is outside scope.
