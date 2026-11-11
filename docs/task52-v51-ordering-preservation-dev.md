# Task 52B V5.1 ordering preservation in local development

This records the original five-case repair. The current development scope and verification are in the [generalization report](task52-v51-ordering-preservation-generalization.md).

The owner-approved case “Buy groceries and maybe stop for coffee.” requires groceries and allows coffee afterward. The raw typed extraction already has groceries 0 → coffee 1. In `backend/journey.py`, `validate_journey` clears source-forward edges and changes the mode to `unspecified` when their quotations contain both stop names and the request lacks a legacy temporal cue or arrow. That condition matches this request. The resulting advanced handoff still carries both visits and their required or optional status, but it has lost the conditional edge. The current router’s source-order fallback can mask the loss in the displayed itinerary. The original regression failed on the effective graph itself before this repair.

## Development boundary

The explicit Python-only entry point `scripts.task52_ordering_preservation_dev.interpret_for_development` accepts a supplied extraction. The default `preserve_order=False` returns the existing legacy result. Normal startup and HTTP routes do not import the adapter. There is no public or environment switch. The supplied extraction is read by an in-memory provider, with no model factory or retry.

The enabled path is deliberately bounded to the five exact reviewed source requests and their frozen clock. It accepts fresh input and leaves pending, edited and broader requests outside the experimental path. It reuses the typed legacy validation and occurrence capture, V5.1 source and graph proof, stop evidence checks, and the reviewed case expectations. This combination checks the raw extraction, the legacy disposition and its calendar and source-occurrence mapping. Only the exact groceries case may differ between raw and effective, and only by deletion of its single proven edge and change of the associated ordering mode. That case copies the original typed graph into both result views. All other differences block planning. A missing or wrong raw edge is never supplied by the adapter.

A compatible result is eligible for the existing local advanced handoff under its normal gates. The adapter creates no session or admission receipt. Requiring the existing admission foundation without a receipt still denies a handoff. The real API continues to use legacy normalization. The historical evaluator also continues to reproduce the original loss.

## Verified scenarios

| Source case | Raw and gated effective result | Existing planner with synthetic evidence |
| --- | --- | --- |
| `extension-repeated/r2` | Distinct Coffee 0 → Museum 1 → Coffee 2, Jersey City, November 6 under the frozen clock, confirmed origin return and inclusive 180-minute maximum | Candidates retain all three visits and return leg. Unknown dwell times leave timing unverified. |
| `journey-04/r2` | Exact SUNY College of Optometry → required coffee, with no added context | Exact synthetic college identity comes first. The test explicitly supplies date and search area through advanced inputs. |
| `extension-partial/r2` | Pharmacy → bank. Coffee remains required with no edge to or from it. Jersey City and relative date retained. | The checked candidates include coffee before, between and after. The display may select a subset. An unreachable required route produces no itinerary. |
| `journey-06/r2` | Groceries required, coffee optional and constrained to follow groceries when selected. No added date, place, budget, duration or endpoint. | Groceries-only and groceries-then-coffee options both work after explicit date and search area inputs. The saved and reopened synthetic records retain the conditional edge, selected order and optionality. A reversed saved order is rejected. |
| `journey-21/r1` | Conflicting pharmacy and bank directions remain a clarification. | No session, venue search or route call. |

The planner takes predecessor closure before filtering optional visits. A separate verified Coffee → optional Museum → Dinner graph produces Coffee → Dinner when the museum is omitted. This exercises the existing planner contract beyond the five exact adapter inputs. It does not broaden the adapter’s source scope.

Regression tests also reject missing or reversed order, duplicate or invented edges, wrong optionality, merged repeated visits, an altered named venue, unsupported or missing endpoints and time limits, missing or borrowed evidence, unknown occurrence mapping, unrelated mutations and extra schema fields. The test save and reopen use the real data mapping with an in-memory database stand-in. No external provider or persistent user data is involved. Distinct repeated visits currently require eligible distinct venue identities, and missing venue or timing evidence still blocks verification.

## Verification and limits

Run the focused boundary and fake-provider tests from the repository root.

```sh
WHERETO_AI_WARMUP_DEV=0 backend/.venv/bin/python -m unittest backend.test_v51_ordering_preservation -v
```

The focused suite exercises the real interpretation and advanced planning functions with supplied extractions and synthetic venue and route evidence. It checks the current API boundary with a fake model and keeps the original historical evaluator sources and artifacts intact. There is no browser activation, broader language support or pending-session integration in this development profile. Production activation requires separate approval.

All nine repair tests passed. The focused backend regression set passed 243 of 259 tests with 16 hosted opt-in skips. It covered journey and phase-B validation, advanced routing and timing, saved plans, provider budgets, admission, and the frozen V5 and V5.1 evidence replays. Frontend passed 285 tests. Lint, TypeScript, the production build and the credential scan passed.

A separate run of the final application modules passed 96 tests. Standard backend discovery was stopped during the long-running, unchanged historical diagnostic simulations. No test failure was reported before the interruption. Full backend completion remains unverified.

Read-only journal inspection matched SHA-256 `241af59ffa81553c98feb1e093c75194d908191504a9e67a6ad16fcc13e49028` and the original ten attempts. OpenAI, Google and Anthropic remain at 7, 2 and 1 respectively. Accounting remains $0.047366625 with $11.952633375 left under the original experiment ceiling. All 324 private files, corrections and the historical halt verified unchanged.
