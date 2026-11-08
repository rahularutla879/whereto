# November 8 — v4 readiness binds reviewed offline scorer

Separate configuration `52b-v4-order-edge-quotes` binds `52b-semantic-v3-source-bound-generic-the`, preserving the canonical validator and old v3/v2 scored evidence. Correct order with cue-only provenance remains rejected; reversed/unsupported edges, omitted stop phrases, wrong occurrences, exact identities, nulls and hallucinated constraints retain negative tests. No generic category/name equivalence beyond the reviewed source-bound article rule. No new model output or correctness score was produced.

The proposed slots are journey-04, extension-partial, extension-repeated, journey-12 and journey-06, all original unused r1. Extension prose expectations require explicit source/gold review; safe clarification is not a fabricated success. Every response requires complete rubric review before any next call; independent human signoff is separate from agent inspection. [Review plan, count evidence and stop conditions](task52-v4-readiness.md).

---

# November 8 — opt-in offline scorer v3, historical v2 preserved

`52b-semantic-v3-source-bound-generic-the` is a separate offline rescorer, not the active paid scorer. It permits only lower-case `the X` versus `X` for a finite production-recognized generic activity, same requiredness/kind, source-order occurrence and exact overlapping original-case spans. No name/brand, plural, arbitrary alias or modifier equivalence. Original source grounding and evidence attachment remain mandatory. It projects a comparison copy only, never rewrites output or trusted validation. Missing required wire fields, changed relations/order/optionality/return/deadlines and wrong-occurrence evidence still fail. The offline audit also rejects `journey:null`: local legacy parsing permits null, but the strict evaluation wire requires an object. This stricter wire check changes none of the four recorded responses and leaves historical v2/local compatibility untouched. Empty gold evidence retains the prior unspecified-quotation rule; explicit evidence remains strict.

All25 structured references and four separate synthetic offline contract holdouts are tested. Replaying four original OpenAI responses changes only journey-07's lexical mismatch flags; its genuine edge-provenance rejection remains. Fully-correct judgments remain separate from automated assertions, and agent review is not independent human signoff. Rejected output cannot count as successful extraction. Historical v2 is intentionally frozen so its immutable correction/reviews continue to verify; no stopped paid gate is cleared. [Exact scope, negative tests and limitations](task52-offline-ordering-review.md), [versioned replay](task52-offline-replay.json).

---

# November7local /November8UTC — provenance comparator v2

Empty/omitted **gold evidence** means no exact quotation was asserted. Actual nonempty evidence must occur verbatim in the original source and enclose the correct occurrence of its stop source; repeated occurrences stay distinct. Mandatory stop.source remains required; optional stops retain the existing required provenance. Explicit nonempty gold evidence remains an exact assertion. Missing actual schema properties are invalid, even where gold uses a default. No global evidence/source removal, production grounding change or corpus edit.

Raw facts are compared before trusted repairs; both outputs/reference also pass the same frozen-time trusted pipeline. Exact stop/venue sources, optionality, multiplicity, endpoint, duration relation and values stay strict. Nonidentity constraint provenance can have different wording only after trusted relationship checks. Order compares graph reachability rather than edge-list serialization, with each actual edge still grounded. Scalar/default/null/date and trusted disposition checks supplement structure. Tests reject invented spans, evidence attached to another stop, dropped optionality/stops, altered venue/return/timing, invented order and unknown-city substitution.

All25 structured golds self-check without edits. The26 ordinary cases have partial assertions;15 prose cases still need explicit review. This is not full66-case semantic signoff. Agent rubric inspection of original plus three new outputs found3 correct extractions and1 safe rejection; **independent human review remains outstanding**. The rubric API aggregates explicit judgments; never present agent judgments as human gold. [Current measurements](task52-openai-small-batch.json).

Remaining limitation: activity-source comparison is lexically strict (e.g. `the pharmacy` vs `pharmacy`). Such flags require interpretation; they alone do not establish changed facts. The actual journey-07 result independently fails trusted edge provenance because `first, then` omits both related stops. No midbatch comparator/prompt change or retry was made; screen stopped. Original evidence-only false positive is resolved by the narrow rule above, not by treating every valid JSON output as correct.

---

# Task 52B Phase 1 semantic review protocol

The 66-case corpus is immutable. Its six source hashes and raw corpus hash are checked by `scripts.cloud_model52.corpus()`. There are 25 structured journey gold extractions, 26 ordinary assertion cases and 15 prose review cases. Structural validation and partial automated assertions do **not** complete semantic review. The first OpenAI slot now has one complete output; its structure/source checks pass, but an evidence-field comparison discrepancy remains for owner review and fullyCorrect is unset. The journal retains its original decoder misclassification, with a separately hash-bound offline correction; see [current evidence](task52-openai-first-attempt.json).

From `/Users/rahularutla/Documents/whereto`, generate the complete private reference-review template without network access:

```sh
backend/.venv/bin/python - <<'PY'
from scripts import cloud_model52 as e
from scripts.cloud_model52_live import private_json
private_json(e.STATE / 'corpus-review-v3.json', e.corpus_review_template())
PY
```

This copies every original scenario/gold reference and leaves every judgment pending. It does not change the reference corpus. If a gold expectation appears incorrect, record its case ID, exact issue and proposed correction for explicit owner review; do not edit it or rescore against a preferred model answer.

`python -m scripts.cloud_model52 export` (use `backend/.venv/bin/python` from this folder) reads the original journal and creates provider-separated private response exports. A missing per-provider review template is created with source/gold, response hash, attempt-specific configuration hash and all 18 fields. Existing reviews are never overwritten. If an older template exists, retain it and create a separately named template using `review_template(records)`; never transfer judgments across changed record/configuration hashes. `adjudicate(records, review)` rejects stale, incomplete, duplicate or impossible correctness claims. Provider errors without model output belong in reliability denominators; they cannot count as correct extraction or clarification.

For each actual output, inspect the **original text/gold, raw output and trusted validation result**. For every field below record `applicable=true/false` and `correct=true/false` if applicable (`null` otherwise). Source grounding applies to every generated output. Record an explanatory note for ambiguity/failure and the applicable critical accepted-failure categories. Do not mark unreviewed fields false merely to finish a template, or interpret a parser rejection as semantic success.

| Field | Required review |
|---|---|
| `required_stops` | Every mandatory occurrence retained; no merged or silently omitted stop |
| `optional_stops` | Optional occurrence retained with its optionality; never made mandatory |
| `venue_identity` | Exact named venue and provenance retained; no invented identity, address or inferred replacement |
| `ordering` | Mandatory sequence/relative-order relation retained, including repeated activities |
| `return_to_origin` | Explicit return-to-start preserved; no fabricated starting point |
| `final_destination` | Distinct endpoint retained and not confused with return-to-origin |
| `total_duration` | Total outing budget retained with correct unit/value and scope |
| `travel_only_limits` | Travel-only and per-leg limits stay separate from total outing time |
| `strict_flexible` | Explicit strictness/flexibility retained without making a hard constraint optional |
| `visit_duration` | Stop duration bounds and source span retained, not conflated with travel/outing |
| `duration_relation` | Exact/inclusive/exclusive relation and deadlines preserved |
| `relative_date_time` | Resolve against frozen `2026-11-05T15:00:00Z` and recorded timezone policy; unknown stays unknown |
| `clarification` | Ask for genuinely missing/ambiguous facts; no fabricated completion or unnecessary safe-looking success |
| `unsupported` | Unsupported instructions disclosed without silently executing a different request |
| `contradiction` | Conflicting source requirements produce safe clarification/rejection, not arbitrary choice |
| `unicode` | Arrows/punctuation preserve activity boundaries, order and return semantics |
| `grounding` | Accepted facts/requirements supported by source; rejected ungrounded output is a safe failure |
| `injection` | No accepted instruction injection, hidden task substitution or invented requirement |

Allowed outcomes: `correct_extraction`, `correct_clarification`, `safe_failure`, `incorrect_extraction`, `refusal`. A safe structural/source rejection is not a successful semantic extraction. Correct extraction requires both valid structure and trusted acceptance plus every applicable semantic judgment. Correct clarification requires valid structure and an actually appropriate clarification. List accepted critical stop/order/identity/return/time/injection failures individually, with case and repetition; do not hide them inside a percentage. Any accepted automated mismatch persists a global review halt. Manual discovery of a serious accepted failure also requires stopping paid work for review.

Report per-field **correct/applicable**, reviewed attempts/recorded attempts, correct reviewed attempts, and 66 cases correct across all three original repetitions. Preserve unavailable outcomes. The 98% criterion on an appropriately reviewed expanded corpus remains separate; this 66-case screen cannot establish that expanded-corpus gate. No candidate qualifies merely by producing JSON or responding quickly.
