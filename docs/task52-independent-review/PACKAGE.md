# Where To? independent semantic review package

Review packet `52b-v51-independent-semantic-review-v1` · Five diagnostic cases and two historical responses

Where To? turns an outing request into a set of visits and constraints for planning. This review checks that the proposed reference interpretations reflect the user’s words and the current product rules. A valid-looking response can still omit a requirement, add a restriction or cite evidence for the wrong visit.

The owner approved the five plain-English interpretations. An independent reviewer still needs to judge each of the 24 checks per case and assess both historical responses. The package includes the evidence needed for this review. Record your judgments in the [blank review form](REVIEW_FORM.md).

## How to review

1. Read each quoted request first and write down what you understand it to require.
2. Compare your reading with each row. Mark **Agree** when the proposed requirement or absence is supported, **Disagree** when you would change it, or **Uncertain** when the wording or policy leaves a material question open. Cite the words that support your judgment and propose a correction or question when applicable.
3. Review every row, including absence checks. **Absent** means the complete quoted request supplies no such requirement. **Applies** means the rubric defines a specific check, which can include confirming that the response adds no date. Review the two historical responses separately using the rules applicable to each assessment.
4. Record any overall disagreement or uncertainty and return the completed form. For evidence checks, make sure wording belongs to the correct occurrence and supports the direction and scope asserted. An exact substring alone can be insufficient. A reference with no prescribed quotation still requires evidence, and a missing required response field differs from an explicit unknown where the response format permits one.

The current V5.1 policy treats a complete activity list as chronological by default, including simple conjunctions used to list visits. A reviewed connector such as Roman-script Hindi “aur” can serve the same role when its scope is clear. Explicit order and flexible placement take precedence within their scope. Optional visits keep their sequence position when included, and skipping one preserves order among remaining visits. Flexible placement leaves attendance required unless the wording makes it optional. Repeated visits keep distinct source positions. Returns and separate destinations are endpoints. Conflicting instructions require clarification. An arrow below means “must happen before” when both visits occur.

For the two requests containing “tomorrow”, the fixed test clock is November 5, 2026 at 15:00 UTC and the calendar time zone is America/New_York. Requests without a calendar expression gain no date from that clock.

## 1. extension-repeated/r2

> Coffee, museum, then coffee in Jersey City tomorrow, return to the starting point within three hours.

Three required visits: Coffee0 → Museum1 → Coffee2, in Jersey City tomorrow relative to the frozen reference. Return to the confirmed origin within an inclusive 180-minute whole-trip limit. Do not invent other constraints.

| ID | Check | Scope | Proposed judgment and source evidence |
| --- | --- | --- | --- |
| 1.01 | Required activities | Applies | Three required visits from “Coffee, museum, then coffee” in source positions 0, 1 and 2. |
| 1.02 | Optional activities | Absent | There is no optional activity. Keep the stated activities required. |
| 1.03 | Exact named place | Absent | No exact venue is named. Keep the activity or place category generic. |
| 1.04 | Required visit order | Applies | Coffee 0 before Museum 1 from “Coffee, museum”; Museum 1 before Coffee 2 from “museum, then coffee”. Coffee 0 before Coffee 2 follows from those two links. A redundant direct link is unnecessary. No reverse or extra order. |
| 1.05 | Flexible or unordered placement | Applies | “Coffee, museum, then coffee” is a complete chronological list under V5.1. No visit has flexible placement. |
| 1.06 | Repeated visits | Applies | “Coffee” at the start and “coffee” after “then” are distinct required occurrences 0 and 2. Keep both, without assuming either must be the same venue. |
| 1.07 | Return to the starting point | Applies | “return to the starting point” requires the confirmed origin. Keep it unresolved until confirmed. Do not infer an address or coordinates. |
| 1.08 | Separate final destination | Absent | “the starting point” is the return endpoint. There is no separate terminal destination. |
| 1.09 | Designated final visit | Absent | Coffee 2 is last among the visits by the stated sequence. The subsequent return is an endpoint action. There is no separate final-visit instruction. |
| 1.10 | Home endpoint ambiguity | Absent | There is no home reference. Do not add or resolve a home endpoint. |
| 1.11 | Whole-trip time limit | Applies | “return to the starting point within three hours” sets an inclusive 180-minute maximum for the whole outing, including the return. |
| 1.12 | Travel-only time limit | Absent | No separate limit is given for time spent traveling. |
| 1.13 | Time spent at each stop | Absent | No time to spend at any stop is specified. |
| 1.14 | Exact, minimum or maximum duration | Applies | “within three hours” means at most 180 minutes for the whole trip. Exactly 180 minutes is allowed. There is no minimum or exact-length requirement. |
| 1.15 | Calendar date and time zone | Applies | “tomorrow” means November 6, 2026 in the fixed Jersey City test context. Preserve the relative wording. If the time zone is unknown, clarify before planning. Do not add a time of day. |
| 1.16 | Budget and transportation | Absent | No budget, currency or mode of travel is specified. |
| 1.17 | Clarification or safe handling | Applies | The activity request is clear as written. Preserve the stated requirements. Ask about any unresolved detail that is required before planning. Extraction alone establishes neither venue availability nor permission to publish a plan. |
| 1.18 | Unsupported additions or omissions | Applies | Check the whole request. Preserve each activity and add no unsupported activity, venue, order, endpoint, location, date, time, duration, price, availability or capability. |
| 1.19 | Conflict or attempt to redirect the AI | Absent | The request has no conflicting directions or instruction to override the app’s rules. |
| 1.20 | Evidence from the request | Applies | Tie each visit to its own occurrence. Use “Coffee, museum” for the list link and “museum, then coffee” for the explicit link. Bind the return, cap, place and date to their own phrases. |
| 1.21 | Group size or people | Absent | No number or description of people is specified. |
| 1.22 | Requested search area | Applies | Preserve “Jersey City” as the requested area. Do not substitute the origin or widen the area. |
| 1.23 | Shared location constraint | Absent | No requirement places the stops in the same venue, building or complex. |
| 1.24 | Clock-time deadline | Absent | “within three hours” is an elapsed-time limit. No clock-time deadline is given. |

## 2. journey-04/r2

> Go to SUNY College of Optometry and then get coffee.

Visit the exact SUNY College of Optometry before getting coffee. Both activities required. Do not invent date, budget, transportation, duration or return requirements.

| ID | Check | Scope | Proposed judgment and source evidence |
| --- | --- | --- | --- |
| 2.01 | Required activities | Applies | Two required visits from “Go to SUNY College of Optometry” and “get coffee”, in source positions 0 and 1. |
| 2.02 | Optional activities | Absent | There is no optional activity. Keep the stated activities required. |
| 2.03 | Exact named place | Applies | Keep the exact name “SUNY College of Optometry” for visit 0. No coffee venue is named. |
| 2.04 | Required visit order | Applies | “SUNY College of Optometry and then get coffee” puts visit 0 before visit 1. No reverse or extra order. |
| 2.05 | Flexible or unordered placement | Applies | “and then” fixes the order of these two visits. Neither has flexible placement. |
| 2.06 | Repeated visits | Absent | No repeated visit is requested. Keep one occurrence per requested activity. |
| 2.07 | Return to the starting point | Absent | No return to the starting point is requested. |
| 2.08 | Separate final destination | Absent | No separate terminal destination is named. |
| 2.09 | Designated final visit | Absent | There is no separate final-visit instruction. Apply the visit order in the order row. |
| 2.10 | Home endpoint ambiguity | Absent | There is no home reference. Do not add or resolve a home endpoint. |
| 2.11 | Whole-trip time limit | Absent | No limit is given for the whole outing. |
| 2.12 | Travel-only time limit | Absent | No separate limit is given for time spent traveling. |
| 2.13 | Time spent at each stop | Absent | No time to spend at any stop is specified. |
| 2.14 | Exact, minimum or maximum duration | Absent | No exact, minimum or maximum duration is specified. |
| 2.15 | Calendar date and time zone | Applies | There is no calendar request. Do not add a date, time window or user-supplied time zone. |
| 2.16 | Budget and transportation | Absent | No budget, currency or mode of travel is specified. |
| 2.17 | Clarification or safe handling | Applies | The activity request is clear as written. Preserve the stated requirements. Ask about any unresolved detail that is required before planning. Extraction alone establishes neither venue availability nor permission to publish a plan. |
| 2.18 | Unsupported additions or omissions | Applies | Check the whole request. Preserve each activity and add no unsupported activity, venue, order, endpoint, location, date, time, duration, price, availability or capability. |
| 2.19 | Conflict or attempt to redirect the AI | Absent | The request has no conflicting directions or instruction to override the app’s rules. |
| 2.20 | Evidence from the request | Applies | Keep the full college name tied to visit 0 and “coffee” tied to visit 1. The evidence for order must connect both visits through “and then”. |
| 2.21 | Group size or people | Absent | No number or description of people is specified. |
| 2.22 | Requested search area | Absent | No geographic search area is specified. Do not invent one. |
| 2.23 | Shared location constraint | Absent | No requirement places the stops in the same venue, building or complex. |
| 2.24 | Clock-time deadline | Absent | No clock-time deadline is given. |

## 3. extension-partial/r2

> Visit a pharmacy before the bank; get coffee whenever convenient, in Jersey City tomorrow.

Pharmacy, bank and coffee are required. Pharmacy precedes bank; coffee may occur before, between or after them. Preserve Jersey City and reference-relative tomorrow. No invented additional constraints.

| ID | Check | Scope | Proposed judgment and source evidence |
| --- | --- | --- | --- |
| 3.01 | Required activities | Applies | Three required visits from “Visit a pharmacy before the bank” and “get coffee”, in source positions 0, 1 and 2. |
| 3.02 | Optional activities | Absent | “whenever convenient” modifies placement. Coffee is required, as are pharmacy and bank. |
| 3.03 | Exact named place | Absent | No exact venue is named. Keep the activity or place category generic. |
| 3.04 | Required visit order | Applies | “a pharmacy before the bank” establishes only visit 0 before visit 1. Add no order to or from coffee. |
| 3.05 | Flexible or unordered placement | Applies | “get coffee whenever convenient” lets coffee go before, between or after the ordered pharmacy and bank visits. Keep pharmacy before bank. |
| 3.06 | Repeated visits | Absent | No repeated visit is requested. Keep one occurrence per requested activity. |
| 3.07 | Return to the starting point | Absent | No return to the starting point is requested. |
| 3.08 | Separate final destination | Absent | No separate terminal destination is named. |
| 3.09 | Designated final visit | Absent | There is no separate final-visit instruction. Apply the visit order in the order row. |
| 3.10 | Home endpoint ambiguity | Absent | There is no home reference. Do not add or resolve a home endpoint. |
| 3.11 | Whole-trip time limit | Absent | No limit is given for the whole outing. |
| 3.12 | Travel-only time limit | Absent | No separate limit is given for time spent traveling. |
| 3.13 | Time spent at each stop | Absent | No time to spend at any stop is specified. |
| 3.14 | Exact, minimum or maximum duration | Absent | No exact, minimum or maximum duration is specified. |
| 3.15 | Calendar date and time zone | Applies | “tomorrow” means November 6, 2026 in the fixed Jersey City test context. Preserve the relative wording. If the time zone is unknown, clarify before planning. Do not add a time of day. |
| 3.16 | Budget and transportation | Absent | No budget, currency or mode of travel is specified. |
| 3.17 | Clarification or safe handling | Applies | The activity request is clear as written. Preserve the stated requirements. Ask about any unresolved detail that is required before planning. Extraction alone establishes neither venue availability nor permission to publish a plan. |
| 3.18 | Unsupported additions or omissions | Applies | Check the whole request. Preserve each activity and add no unsupported activity, venue, order, endpoint, location, date, time, duration, price, availability or capability. |
| 3.19 | Conflict or attempt to redirect the AI | Absent | The request has no conflicting directions or instruction to override the app’s rules. |
| 3.20 | Evidence from the request | Applies | Use “a pharmacy before the bank” for the one required order and “get coffee whenever convenient” for visit 2’s placement. Keep Jersey City and tomorrow tied to their own wording. |
| 3.21 | Group size or people | Absent | No number or description of people is specified. |
| 3.22 | Requested search area | Applies | Preserve “Jersey City” as the requested area. Do not substitute the origin or widen the area. |
| 3.23 | Shared location constraint | Absent | No requirement places the stops in the same venue, building or complex. |
| 3.24 | Clock-time deadline | Absent | No clock-time deadline is given. |

## 4. journey-06/r2

> Buy groceries and maybe stop for coffee.

Groceries required; coffee optional. If included, coffee follows groceries. If omitted, groceries remain required. No invented context.

| ID | Check | Scope | Proposed judgment and source evidence |
| --- | --- | --- | --- |
| 4.01 | Required activities | Applies | “Buy groceries” makes groceries the sole required visit, in source position 0. |
| 4.02 | Optional activities | Applies | “maybe stop for coffee” makes coffee, in source position 1, the sole optional visit. Keep it represented as a choice. |
| 4.03 | Exact named place | Absent | No exact venue is named. Keep the activity or place category generic. |
| 4.04 | Required visit order | Applies | “Buy groceries and maybe stop for coffee” puts groceries before coffee if coffee is included. When skipped, groceries remain required and there is no remaining pair to order. |
| 4.05 | Flexible or unordered placement | Applies | The conjunction joins a complete activity list. “Maybe” makes coffee optional. If included, its position follows groceries. |
| 4.06 | Repeated visits | Absent | No repeated visit is requested. Keep one occurrence per requested activity. |
| 4.07 | Return to the starting point | Absent | No return to the starting point is requested. |
| 4.08 | Separate final destination | Absent | No separate terminal destination is named. |
| 4.09 | Designated final visit | Absent | There is no separate final-visit instruction. Apply the visit order in the order row. |
| 4.10 | Home endpoint ambiguity | Absent | There is no home reference. Do not add or resolve a home endpoint. |
| 4.11 | Whole-trip time limit | Absent | No limit is given for the whole outing. |
| 4.12 | Travel-only time limit | Absent | No separate limit is given for time spent traveling. |
| 4.13 | Time spent at each stop | Absent | No time to spend at any stop is specified. |
| 4.14 | Exact, minimum or maximum duration | Absent | No exact, minimum or maximum duration is specified. |
| 4.15 | Calendar date and time zone | Applies | There is no calendar request. Do not add a date, time window or user-supplied time zone. |
| 4.16 | Budget and transportation | Absent | No budget, currency or mode of travel is specified. |
| 4.17 | Clarification or safe handling | Applies | The activity request is clear as written. Preserve the stated requirements. Ask about any unresolved detail that is required before planning. Extraction alone establishes neither venue availability nor permission to publish a plan. |
| 4.18 | Unsupported additions or omissions | Applies | Check the whole request. Preserve each activity and add no unsupported activity, venue, order, endpoint, location, date, time, duration, price, availability or capability. |
| 4.19 | Conflict or attempt to redirect the AI | Absent | The request has no conflicting directions or instruction to override the app’s rules. |
| 4.20 | Evidence from the request | Applies | Tie groceries and coffee to their own phrases. Use the complete “groceries and maybe stop for coffee” wording for order and “maybe stop for coffee” for optional attendance. |
| 4.21 | Group size or people | Absent | No number or description of people is specified. |
| 4.22 | Requested search area | Absent | No geographic search area is specified. Do not invent one. |
| 4.23 | Shared location constraint | Absent | No requirement places the stops in the same venue, building or complex. |
| 4.24 | Clock-time deadline | Absent | No clock-time deadline is given. |

## 5. journey-21/r1

> Visit the pharmacy before the bank, but the bank before the pharmacy.

Preserve both pharmacy and bank. Detect the contradictory ordering instructions. Ask for clarification and do not publish a plan until resolved.

| ID | Check | Scope | Proposed judgment and source evidence |
| --- | --- | --- | --- |
| 5.01 | Required activities | Applies | Keep one required pharmacy visit and one required bank visit. Both are named in each side of the conflicting instruction. |
| 5.02 | Optional activities | Absent | There is no optional activity. Keep the stated activities required. |
| 5.03 | Exact named place | Absent | No exact venue is named. Keep the activity or place category generic. |
| 5.04 | Required visit order | Applies | “pharmacy before the bank” and “bank before the pharmacy” give opposite directions for the same visits. Preserve the conflict. Admit no order or plan pending clarification. |
| 5.05 | Flexible or unordered placement | Applies | The two directions conflict. Neither stop was given flexible placement. Do not treat this as an any-order outing. |
| 5.06 | Repeated visits | Absent | Each place is mentioned twice as part of the conflicting instructions. The text does not request a second visit to either. |
| 5.07 | Return to the starting point | Absent | No return to the starting point is requested. |
| 5.08 | Separate final destination | Absent | No separate terminal destination is named. |
| 5.09 | Designated final visit | Absent | There is no separate final-visit instruction. The conflicting directions leave the order unresolved. |
| 5.10 | Home endpoint ambiguity | Absent | There is no home reference. Do not add or resolve a home endpoint. |
| 5.11 | Whole-trip time limit | Absent | No limit is given for the whole outing. |
| 5.12 | Travel-only time limit | Absent | No separate limit is given for time spent traveling. |
| 5.13 | Time spent at each stop | Absent | No time to spend at any stop is specified. |
| 5.14 | Exact, minimum or maximum duration | Absent | No exact, minimum or maximum duration is specified. |
| 5.15 | Calendar date and time zone | Applies | There is no calendar request. Do not add a date, time window or user-supplied time zone. |
| 5.16 | Budget and transportation | Absent | No budget, currency or mode of travel is specified. |
| 5.17 | Clarification or safe handling | Applies | Ask which visit should come first and keep both required. Block planning until the user resolves the conflict. |
| 5.18 | Unsupported additions or omissions | Applies | Check the whole request. Preserve each activity and add no unsupported activity, venue, order, endpoint, location, date, time, duration, price, availability or capability. |
| 5.19 | Conflict or attempt to redirect the AI | Applies | Both “before” instructions apply to the same pair and conflict. Do not choose one, invent more visits to satisfy both, call tools or claim a booking. The wording is a conflict in the outing request. |
| 5.20 | Evidence from the request | Applies | Tie both clauses to the same two occurrences. Cite “pharmacy before the bank” and “bank before the pharmacy” when explaining the conflict. |
| 5.21 | Group size or people | Absent | No number or description of people is specified. |
| 5.22 | Requested search area | Absent | No geographic search area is specified. Do not invent one. |
| 5.23 | Shared location constraint | Absent | No requirement places the stops in the same venue, building or complex. |
| 5.24 | Clock-time deadline | Absent | No clock-time deadline is given. |

## Historical responses for separate review

### H1. journey-07/r1 — insufficient evidence for the edge

> Go to the pharmacy first, then the supermarket.

The model returned pharmacy 0 before supermarket 1 and cited only “first, then” for that relationship. The visit direction matches the request. The cited words omit both visits, so they do not tie the edge to its two occurrences. The historical evaluation classified this as a provenance error and blocked the response. Under V5.1 the full clause “the pharmacy first, then the supermarket” independently establishes the direction, and the unchanged saved citation still fails the evidence check.

In your review, judge the requested direction, whether the response’s citation establishes ownership, and whether blocking that response was appropriate.

### H2. extension-repeated/r1 — accepted unsupported edge under historical V4

> Coffee, museum, then coffee in Jersey City tomorrow, return to the starting point within three hours.

The response kept three required visits and returned both of these edges.

| Edge | Evidence supplied by the model |
| --- | --- |
| Coffee 0 → Museum 1 | “Coffee, museum, then” |
| Museum 1 → Coffee 2 | “museum, then coffee” |

It also preserved Jersey City, “tomorrow”, return to the starting point and the inclusive 180-minute whole-trip maximum.

**Historical finding.** The existing validator accepted the graph at interpretation handoff. Under the historical V4 rubric only Museum 1 → Coffee 2 was supported. The “then” in the first quote introduces the later coffee. The extra Coffee 0 → Museum 1 edge was a critical accepted ordering error under that rubric. The independent V4 guard blocked the graph while recognizing Museum 1 → Coffee 2.

**Current V5.1 reassessment.** The complete activity list now establishes Coffee 0 → Museum 1 through the comma-separated list, and “museum, then coffee” establishes Museum 1 → Coffee 2. The ordering-only replay verified the saved graph and its evidence under V5.1. The first edge is grounded in the list itself, so its trailing “then” supplies no additional proof for that pair. This ordering result leaves full-response correctness open to independent review. The original classification remains the result under the original rules.

In your review, assess the accepted error under V4 and the same graph and quotations under V5.1 separately. This historical response is repetition 1. Case 1 above is the reference expectation for proposed repetition 2.

## Source record

These identifiers let the project maintainer verify the evidence reproduced above. The review itself can be completed using this package and the form.

- Reviewed prompt `52b-cloud-v5.1-owner-list-order-REVIEWED-v1` with complete prompt SHA-256 `1741e5b5ae344fff0e4fff1fba2c4b45fd73b0b86baf73bdae35607f4b1919c9`.
- Proposed rubric `52b-q1-rubric-v3-owner-decisions-v5.1-PROPOSED` with file SHA-256 `fd0686aeb3b136d34da7cf586fa5413593500c95837c45fb302d0d179cf93abe`.
- Original 66-case corpus file SHA-256 `5c7be9828fd6690f5b11ef38bee019eff5a9962adaccef13ee572fca2ac8549f`.
- Selected case sources, SHA-256 over the exact UTF-8 request text.

| Case | Source SHA-256 |
| --- | --- |
| extension-repeated/r2 | `7183ad071492d60d68a65a12f2e6b8cbdf77d25efdf1dc2e466152ca9d42bd6c` |
| journey-04/r2 | `608d5f41198d2d658bc288520dc8513eef6f2419d3779fb6ecd87137297d450e` |
| extension-partial/r2 | `4038a95c47f7fc546989b1ed84ef43aac9fd586a18ad2a06c1e6d0415e42497f` |
| journey-06/r2 | `abf56895dfb84aa1e7f3447b90f9295aa00155593408211514e0f42bf7473d1d` |
| journey-21/r1 | `5d88d74b325fd6b2f4c3178500a842dac423cd2ed9723305f8762504eea703da` |
