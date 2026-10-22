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
