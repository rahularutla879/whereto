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

- `where-to-512422` has Places API (New) and Routes API enabled and **Free Trial billing linked by the owner**, no credentials, and a saved $50/month account-wide alert budget (explicitly approved because project-only selection was unavailable). Maps JavaScript remains disabled. Lower quotas are verified; exact values and remaining approval steps are in [docs/billing-safeguards.md](docs/billing-safeguards.md). Task 39 is partial; Task 40 has not started.
- Keep `VENUE_DATA_MODE` absent or `mock`; live provider access is deliberately locked off in code. Do not link billing, start a trial, enter payment details, accept financial terms or issue live provider requests without explicit authorization. Billing setup does not itself authorize live use.
- Future adapters must use the shared process/outing budget before every request/page/retry and enforce candidate/matrix limits before routing. No hidden SDK retries, per-itinerary network calls or silent activity omissions. Mock planning and local AI behavior retain their existing rules.
- Future credentials must be backend-only and limited to necessary APIs/access. API keys require verified public egress IP restrictions and an approved untracked secret location; an OAuth service identity requires separately verified minimal permissions and short-lived token handling. No invented local/host IP, unrestricted key, `NEXT_PUBLIC_*` key, browser key or committed secret. Defer credentials while appropriate restrictions cannot be established.
- Quotas, free allowances and process-local limits do not guarantee a hard monthly spending ceiling. Saved $50 actual-cost alerts at 50%, 90%, 100% ($25/$45/$50) exclude credits, may lag usage and are notifications only. The budget covers all projects linked to the account, currently only Where To. The trial is not authorized for paid upgrade. Proposed quota/application increases are not approved or applied. Reverify quotas, budget recipients and credential restrictions after financial setup and before any approved live use.
