# Task52B — V5.1 signed offline evaluation integration

Implementation **`52b-v51-signed-offline-evaluator-v1`**, baseline clean `1fe2e9860fac2c22bb7f17a9b10a112caf31eeda`. [Exact build/profile](task52-v51-evaluator-build-v1.json), [five-case fake evidence](task52-v51-evaluator-fake-results-v1.json), [verification](task52-v51-evaluator-verification-v1.json). This is temporary fictional-state execution, not a live evaluator, human certification, financial grant or production activation.

## What is reused

Frozen Q4A–Q4C sources and manifests remain unchanged. Reuse includes Q4C's strict canonical JSON/duplicate/type/size checks, Ed25519 key/trust/revocation and role separation, role-data schemas/token bounds, exact historical SQLite DDL, FULL-sync reservation anchors, immutable hash-linked scope/start/intent/outcome/review/halt records, global nonce/single-use checks, exposure accounting, filesystem locking, crash checkpoints and closed FakeTransport.

The old protocol hardcodes V4 module-global plan/scorer/auth dependencies. `task52_v51_eval_protocol` binds the **same verified function code objects** into a private fixed namespace containing the V5.1 plan, scorer and auth adapter. Each method uses unchanged code; the standard contextmanager wrapper is reconstructed around its bound generator. There is no source/bytecode rewriting, exec, import hook, monkeypatch of frozen modules or caller-selectable profile/callback. The registry is separate. Old internal Q4C build checks still run; new checks additionally verify the V5.1 build on factory creation and before directory/database access. Tests run the inherited security algorithms against this fixed profile and separately rerun original Q4 security tests.

This deliberate adapter avoids copying or editing the financial/state/recovery engine. It is current verified local code execution, not execution of an unverified historical Git snapshot. It is also **not a hostile-Python/OS sandbox**: arbitrary trusted local code can edit memory/files. Real code/clock/trust control and independent humans remain future security requirements. No current approval can open the real paid directory for writes.

## New purpose-specific components

* `scripts/task52_v51_eval_identity.py`: exact new build allowlist and fixed plan/binding, additionally verifying frozen Q4C and V5.1/B2 artifacts. Bind reviewed prompt1741e5…, configuration4239dd…, all19 examples, canonical/wire schemas, B2 dependency/source identity, original corpus66, proposed V5.1 rubric/scorer/policy, five-case owner-product record, original ten-row root/corrections and selected source/payload/rubric hashes. No paid authority.
* `scripts/task52_v51_eval_auth.py`: reuse canonicalization, Trust, role-data validation and malformed-input refusal. The small detached-verification glue binds a **new signed envelope version/audience/purpose and build**; the OpenSSH verification/check algorithm remains Q4C's. The reusable synthetic Trust format and role-specific namespaces stay unchanged. Cross-version packets refuse in both directions; shared trust format does not make V4 grants valid for V5.1. Every Verified fact still has execution_authorized=false.
* `scripts/task52_v51_eval_scoring.py`: finite five-source three-axis mechanical checks, using unchanged strict parser/decoder, source evidence helpers and source-bound generic-article comparison. No general semantic parser or independent full-correctness assignment.
* Test modules only: temporary synthetic signers, authored fake outputs, wrong-output/authorization probes, inherited crash/concurrency tests and evidence generation. No signing/enrollment utility is added to runtime tools.

Sources under backend production, active prompts, Qwen, frontend, saved/session/provider admission and default-OFF V4 observer do not change. New modules are not imported by application startup. `live_dispatch` is the original unconditional refusal. There is no HTTP client, credential/account loader, live environment/CLI/API switch, real writer, issuer, operator enrollment or real approval sidecar.

## Five-case fake execution

Order remains extension-repeated/r2 → journey-04/r2 → extension-partial/r2 → journey-06/r2 → journey-21/r1. Fictional signed owner/rubric/readiness/execute/review facts are bound to one factory-created temporary exact-schema database. Three newly generated disposable test keys represent owner/reviewer/operator groups; they do not prove three independent humans. All real review packages remain unapproved.

State sequence is unchanged: signed scope → durable START → full SQLite reservation → immutable INTENT → one closed fake exchange → OUTCOME → signed24-field fictional REVIEW → next-slot eligibility. No retries, refunds or charge-anchor updates. Failed/uncertain operations retain the full charge. Actual real prefixes are never copied: fictional baseline rows contain synthetic markers/charges and original consumed slot IDs, with separate opaque historical comparison identities.

Three axes remain distinct:

| Axis | Reported meaning |
| --- | --- |
|A Raw extraction|Original immutable output hash, complete structure/usage, finite source facts and extractionFailures. fullyCorrectIndependent remains null. A safe guard block does not make a hallucination correct.|
|B Actual B2 legacy|Complete fake-provider interpretation at the frozen Q1 clock; disposition/result hash, effective graph and order preservation. No graph repair.|
|C V5.1 guard|Raw source-first ordering proof combined with unchanged legacy checks and occurrence mapping. Candidate-only, blocked, known effective-order loss, or appropriate clarification. planningAuthorized always false.|

Q4C's mechanicalFailures stop-vector key is retained for protocol compatibility. It combines explicit raw extractionFailures with separately identified systemFailures (for example unknown effective occurrence mapping); the latter is not mislabeled a model hallucination. Unknown mapping is fatal. Correct raw grocery/optional-coffee order can have known legacy **graph loss with unchanged occurrences**: report blocked_by_legacy_effective_order_loss, not a raw extraction error or accepted plan. Fictional diagnostic progression may acknowledge that known limitation through a synthetic review; this is not a decision authorizing real paid continuation past such a limitation.

Correct fake repeated visits retain0→1→2, origin return and inclusive180. Named college identity/order, independently required flexible coffee, and optional sequencing are checked. Contradiction must retain both stops and quote both conflicting clauses, clarify and admit no graph/plan. Correct JSON alone cannot pass these checks. Invented scalar/dwell/deadline/shared-place/endpoint/date requirements, borrowed return/time evidence, wrong statuses, missing required reachability, reversed/extra edges, merged repeats or inappropriate clarification are fatal.

## Financial and recovery boundaries

Original real state stays OpenAI7/Google2/Anthropic1=10/594,$0.047366625 retained/$11.952633375 remaining, all324 private files/corrections and historical halt unchanged. Fake default baseline is ten fictional1,000,000-nanodollar anchors, deliberately **not** original financial records. Five new fictional full2,500,000 anchors retain12,500,000 total, even when usage-based fictional estimates are lower. Rates125/500 nanodollars per token are historical fake-test constants, not verified current prices. None is real authorization, spending, token counting or account evidence.

Preserve original$12/594/198-per-provider/12k-input/2k-output/concurrency1/retries0 and proposed child5/$0.0125. Real monetary/current provider facts remain unknown. Existing process-exit tests cover seven checkpoints and competing operators. They do not establish power-loss, disk corruption or distributed durability. Lost fixture registry, corrupt facts/prefix/schema, uncertain send, missing review, disagreement, wrong build/source/slot and expired/replayed permissions all refuse; historical or child halt cannot be cleared to retry.

## Historical comparison and next requirements

Replay the unchanged27 Qwen/seven OpenAI evidence separately. The original repeated-coffee V4 accepted critical error, v3 journey-07 provenance rejection, provider errors, decoder correction, prompt cohorts/source pins and charges remain historical facts. New V5.1 accepts the intended repeated-coffee order, while both historical dinner/drinks outputs omit required V5.1 order. No historical score or response is rewritten, and fake tests are not model qualification.

Offline readiness for owner review requires passing the verification record, not real dispatch. Missing real gates remain: independent24-field review of the five source rubrics/two historical failure mechanisms; real protected role enrollment/trust/clock/code controls; append-only original-journal adapter; a separately reviewed live V5.1 build/transport and exact purpose; authorized fresh account/key/model/pricing/credits/terms/rates/complete-input counts; final exact-slot/full-reservation financial and one-operation permissions; independent response review before another call. Decide explicitly how real diagnostics treat known legacy order loss; no plan can be authorized from it. No general B–E extraction is added here.

Broader66-case gold, five proposed unresolved fields, seven historical independent response reviews,29 bounded-grammar unknowns and original expanded/held-out qualification gates remain open. Gemini Developer API HTTP400/IP and Anthropic grammar-compilation blockers remain unchanged. No production model selection, activation, Maps, billing, infrastructure/migration or Task53 work.
