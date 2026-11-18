# Task52B — deterministic count supervision and fresh GET proposal

Baseline `3e2ba623e15b3f0ce73286775bb9acc62a3432ac`. [Count build v3](task52b-count-only-build-v3.json), [GET build v3](task52b-model-get-build-v3.json), [GET proposal v2](task52b-model-get-PROPOSED-v2.json), [exact verification](task52b-both-readiness-verification-v1.json).

**Offline preparation passed. No actual credential value, provider request, live scope or send authorization was used/created.**

## Count root cause and correction

The new actual count supervisor→child→source/evidence/permission checks→credential loader→local TLS regression failed against the unchanged baseline: `verify_supervision`, old line329, `count_worker_identity`, wire claim present, no HTTP delivery. It had the same reference-sensitive `marshal.dumps(CountOnlyHTTPS.exchange.__code__)` defect as GET: entering the method and retaining constants changed the serialization without changing the code.

Count now reuses the unchanged `task52b_code_identity.py` scheme `52b-source-compiled-code-v1`. Full typed code/constants/defaults are checked against independently compiled SHA-pinned source and expected build values, with exact namespace/function/class/constructor bindings. Seventeen selected count callables include the wire/TLS/dial/writer/loader/metadata/guards and prior-GET/permission validators. Source, normalized bootstrap, interpreter, CA, private-file checks, exact frozen bytes, durable INTENT before key load, one-use claims and terminal no-retry behavior remain. Runtime facts use `identityScheme` and `loadedWireIdentitySHA256`; older marshal facts are never reinterpreted.

Only two misleading fake-exchange process tests were replaced by eight integrated count tests. Existing credential/CLI/PID/observation/protocol/TLS tests remain. No frozen evaluator, journal or prompt/schema artifact changed. Prior build manifests remain intact as historical source identities; independently versioned v3 manifests select current source.

## Before/after and integrated verification

The unchanged positive regression first failed (1failure). After migration it passed (1pass). Both integrated suites then passed15tests. The final full focused cohort passed **116tests in153.301s**, plus **15frozen-compatible tests in1.356s**, with final0failures/errors/skips. The final count suite also loads the original Git-pinned defective count code as a negative control and still sees `count_worker_identity`; the corrected actual exchange succeeds. Both runners repeat in fresh isolated parent/child interpreters and retain replay refusal.

The harness uses actual validators, permission/evidence checks, credential loader, immutable writer, supervisor, worker and exchange, not a replacement provider method. Only clearly fictional source/config/evidence/key files, a fixture CA and guarded loopback DNS are supplied. The count server asserts exact frozen body SHA, project and path. Audit hooks assert durable consumption/INTENT before opening the fictional key. No private owner evidence or credentials are copied. Test support remains excluded by the existing image `backend/*fixture*.py` rule.

Cases cover401/403/400, malformed JSON, zero/bool/excess counts; crashes before/after INTENT and after send; competing supervisors, replay, modified source/build/bootstrap/metadata/wire/constants/dial/class; missing/Read-only Write evidence and an integrity-valid but expired GET. Both CLI profiles refuse inference, retries and each other's operation. The expired fixture was strengthened after the initial integrated run to test freshness rather than a corrupted hash; the final run verifies `prior_evidence_stale` specifically. No deadline or guard was relaxed.

## Exact fresh GET proposal

**`52b-model-get-owner-3e2ba62-v1`** is distinct from both consumed readiness scopes. Future authority is limited to one empty-body **GET** `https://api.openai.com/v1/models/gpt-6-luna`, existing restricted key/project `proj_E4EfEvC5uQYN4nqFaYZoo3I4`, zero POST/inference/retries. Its directory and `.send-authorization.json` do not exist. No model response, revision or expiry is invented. New validated evidence would retain the same UTC-day AND maximum24-hour rule. Original GET expiry remains November18,2026,00:00UTC; old consumed facts/authorizations are not renamed or reset.

Before any real GET, the owner must separately approve exactly this scope/endpoint/project/model with no additional requests. Then the reviewed private enrollment must bind the actual approval, source build, existing credential identity and one-use scope, revalidating all checks. This checkpoint creates no such authorization and runs nothing automatically.

## Count readiness and remaining gates

Count transport/supervision is technically prepared and passes the integrated flow. **Live evidence enrollment is deliberately still blocked.** Proposed count scope `52b-count-only-owner-3ec6b68-v1` and frozen first-slot SHA `70939877e0df3fca79fb68cab25d5449ae2533ec31892ed91b762ddbd2c8e6d1` remain unchanged. Its prior-GET selector still points to the expired original pair, not the proposed GET. No successful new GET exists and no selector/binding was automatically updated.

After an actual successful GET, count requires a separately reviewed source/evidence binding to that real scope/build/raw and validated result, fresh independently observed Write evidence (the existing receipt is stale), and separate owner count-send approval. Permission receipts and old metadata must be preserved rather than retimestamped. This will require explicit evidence/configuration enrollment; the current runner is not claimed live-ready merely because its synthetic path passes. No inference, qualification, dollar allowance or application financial authority follows from a count.

## Preserved records and limits

Read-only checks preserve the original13-file pair, failed10-file GET scope/auth, the unchanged identity helper, count proposal/binding and old manifests, all five frozen payload pairs, ten paid attempts,$0.047366625 accounted,$11.952633375 remaining,324private files and persistent halt. Actual model/permission availability remains untested. Dependency consistency, source/diff and secret-pattern checks pass; configured-value scanning is not run because it would read real secrets. Full backend/B2/SQL/Redis, frontend/build/browser/images/cloud checks were not rerun or claimed; production startup, financial SQL and application behavior are unchanged. Handbook17 updated,14/15 reviewed unchanged, all20chapters retained. No financial grant, provisioning, model selection, public activation or Task53.
