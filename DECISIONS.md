# Technical decisions

This record began with source inspection on October 19, 2026, before Git was initialized; it does not reconstruct earlier project history. Reasons below are limited to code comments, documented behavior, or explicit owner requirements.

## Confirmed current choices

| Choice | Evidence and established reason |
| --- | --- |
| Next.js App Router, React, TypeScript, Tailwind CSS | Present in package.json and app/. The original reason for selecting this stack is not recorded. |
| Client-side rules and local fictional catalog | app/page.tsx calls makePlans directly; README identifies this as a frontend demo without external APIs. No AI provider is selected. |
| Conservative parsing; reject unsupported/ambiguous input instead of partial plans | lib/request.ts, lib/planner.ts, and tests enforce requested activities without unrelated substitutions. |
| Hard limits precede preference ranking | lib/planner.ts filters capacity, cost, travel, date, and timing before scoring. Preference must not bypass feasibility. |
| Preserve requested activity order; return at most three distinct options | Planner enumerates venue combinations and deduplicates strategy winners. This preserves requested order and avoids duplicate recommendations; the original three-option product rationale is not recorded. |
| Explicit fictional event dates and Baltimore calendar | Fixed fixtures demonstrate scheduled events; the date helper uses America/New_York and tests inject a reference day for deterministic results. |
| Local SVG artwork and system fonts | components/artwork.tsx and app/globals.css; README states no remote images/font downloads. Original styling rationale is not recorded. |
| Build with next build --webpack | Explicit package.json script. Reason for choosing Webpack is not recorded. |
| Six concise continuity documents; preserve README | Owner requirement for beginner-friendly continuity without extra bug/feature/flow documents. |

## Proposed future components — not selected or implemented

- Real venue/event data and routing providers: evaluate in Stage 1; no vendor commitment or paid-service approval exists in this record.
- AI interpretation/conversation, interactive map, storage, saved versions, and sharing: product roadmap only. Provider, database, authentication, and hosting choices remain open.

## October 19, 2026 — private GitHub backup

At the owner's request and after explicit approval to create the repository, initialize Git in the existing folder and use the private [rahularutla879/whereto](https://github.com/rahularutla879/whereto) repository as `origin`. Use `main` and the `prototype-v0.1` checkpoint tag. Preserve application files and exclude credentials, environment files, generated outputs, dependencies, and local settings. Browser-based GitHub CLI authentication keeps passwords and access tokens out of chat and the repository. No deployment or automatic backup service is configured.

Record future significant decisions with date, choice, reason, and relevant tradeoffs. Do not turn options into commitments without an actual decision.
