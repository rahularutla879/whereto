# 09 — Validation Source Grounding and Ordering Rules

[Course contents](README.md) · [Glossary](GLOSSARY.md)

## Grounding means showing where a claim came from

**Source grounding** checks whether an extracted requirement is supported by the user's actual words. Developers need it because models can return plausible, well-formed statements the user never requested. Where To? specifically needs correct activity multiplicity, ordering, return meaning, budget scope and date relations before expensive planning begins.

**Provenance** is the record of a claim's source. A quote being present in the sentence is necessary for several validators, but not sufficient to establish the claimed relationship. “Coffee, museum, then coffee” contains all three labels; it does not make the word “then” evidence for every possible pair under the frozen V4 policy.

From [backend/journey.py](../../backend/journey.py), `validate_journey`:

```python
def grounded(s): return bool(s) and s.casefold() in raw.casefold()
if [s.source for s in j.stops] != ai.activities:
    return REPHRASE, True
```

Line 1 defines a nonempty, case-insensitive source-membership check. Line 2 compares ordered stop sources to extracted activity phrases. Line 3 blocks on mismatch, returning a rephrase message and a clarification flag. Inputs are the raw request and the proposed extraction; output is a disposition, not a venue list. The larger function checks quotes, durations, endpoints, optional evidence and edges. Membership alone does not prove full semantics; the known ordering error demonstrates that limit.

## Occurrences, edges and cycles

An **occurrence** is a particular requested visit. Coffee0 and coffee2 may share a category but have different positions and constraint ownership. A **directed graph** is nodes joined by directional edges; `before: 1, after: 2` means visit 1 precedes visit 2. A **partial order** constrains some pairs while leaving others free. A **cycle** such as pharmacy→bank→pharmacy is contradictory and cannot produce a valid visit order.

`Journey.consistent` validates references and detects cycles. `validate_journey` independently checks source evidence. `normalize_extracted_references` and `normalize_explicit_durations` are active legacy normalization; the duration helper delegates into [duration_preparation.py](../../backend/duration_preparation.py) after the B2 extraction. A graph being acyclic is not proof it matches the sentence.

## Current runtime versus research policy

| Context | Plain list | Explicit pair | Authority |
|---|---|---|---|
| Active ordinary planner | Retains source list order | Validated full adjacent chain can stay ordinary | Current runtime |
| Active advanced unspecified Journey | Retains source order during shortlist | Constrained/partial graphs govern allowed permutations | Current legacy checks, with known gaps |
| Frozen Ordering V4 | Independently proven unordered list has no mandatory graph edges; may propose audited projection | Requires finite source-owned proof and reachability | Offline/default-OFF observer only |
| Owner-requested V5 | Bounded itinerary lists default sequential; explicit flexibility/partial constraints take precedence | Requires a new versioned contract | Committed offline prototype at `b1efe96`; no runtime integration |

Do not confuse “ordinary code happens to preserve source order” with “a source-first policy proved the user required every adjacent edge.” Do not call V5 implemented application behavior. It changes the expected meaning of historical list cases and needs versioned rubrics/review rather than silently changing earlier scores.

## The known unsafe branch

Legacy code can remove grounded forward edges for plain lists with no explicit ordering cues. With a sentence containing “then,” it uses broader cue/quote checks; the recorded repeated-coffee extraction's extra 0→1 edge survived while valid 1→2 also survived. Another legacy limitation can erase true start/finish edges. V4 independently detects these problems in raw copies, but the observer never changes responses or authorizes planning. See [the policy](../../docs/task52-ordering-policy-v4.md) and [enforcement design](../../docs/task52-ordering-enforcement-design.md).

**Absence proof** means independently establishing that a requirement is not present before removing a model assertion. It is stronger than “the model was probably over-specific.” V3/V4 experiments preserve raw errors even when an audited empty-graph projection is proposed. Unknown wording should clarify rather than gain authority from a guess.

## Other validation remains necessary

`source_constraint_issues` checks bounded numeric/source claims; date resolution uses explicit calendar rules; manual preferences override only their intended fields. A per-person budget must not be multiplied into a group budget. “Under five” excludes exactly five; “within five” includes it. Whole-trip duration differs from inter-stop travel. Home differs from the current origin unless explicitly linked.

[validation_phases.py](../../backend/validation_phases.py), [source_preparation.py](../../backend/source_preparation.py) and [planning_admission.py](../../backend/planning_admission.py) provide versioned preparation and internal admission foundations. Ordinary startup keeps the admission-foundation guards as no-ops; only an explicit Python test scope installs the foundation contract. This is separate from active Task 51 capacity admission. They are not a universal semantic parser or deployed distributed authorization. If source evidence is uncertain, inspect the exact branch/test and retain the uncertainty; do not turn a passing finite probe corpus into a natural-language correctness guarantee.

## Five key takeaways

1. Grounding links claims to actual source meaning.
2. Repeated visits need separate occurrence IDs.
3. Acyclic does not mean correct.
4. Legacy order behavior and V4/V5 policies differ.
5. Unknown meaning must not become planning authority.

## Check your understanding

09.Q1. What is provenance?
09.Q2. Why are two coffee stops not one node?
09.Q3. Can an acyclic edge be wrong?
09.Q4. Does the V4 observer enforce its decision?
09.Q5. Why version V5 expectations?

## Code-reading exercise — 09.R

Read the forward-edge removal condition in validate_journey. Compare it to the later edge cue test.

## Practical exercise — 09.P

Write the node/edge tables for “coffee, museum, then coffee” under frozen V4 and proposed V5, clearly labeling both policies.

See [separate answers and guidance](EXERCISE_SOLUTIONS.md#chapter-09).

[Previous chapter](08-ai-interpretation-qwen-ollama-prompts-and-structured-json.md) · [Contents](README.md) · [Next chapter](10-planning-algorithms-filtering-scheduling-and-ranking.md)
