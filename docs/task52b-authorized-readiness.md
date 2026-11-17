# Task52B — first authorized OpenAI readiness result

Baseline `63ecdbbbf520a4e8154c81341eb8d4394b3c38ce`, November17,2026.
[Sanitized outcome/verification](task52b-authorized-readiness-result-v1.json) · [exact owner scope](task52b-readiness-owner-authorization-v1.json) · [source/runtime build](task52b-readiness-live-build-v1.json).

**The model GET succeeded; the count POST was refused. The scope is permanently consumed.** No inference or retry occurred.

| Exact authorized operation | Complete HTTP outcome | Validation |
| --- | --- | --- |
| GET `/v1/models/gpt-6-luna` | 200,19:48:46UTC | expected model object and exact ID validated |
| POST `/v1/responses/input_tokens` | 401,19:48:47UTC | `invalid_request_error`; missing scope `api.responses.write`; no count |

Only these two authenticated API requests were attempted, using the same enrolled restricted key and `OpenAI-Project: proj_E4EfEvC5uQYN4nqFaYZoo3I4`. The project association/permissions were bound to the prior owner dashboard receipt; this was not an independent administration/billing account audit. The count body SHA remains `70939877e0df3fca79fb68cab25d5449ae2533ec31892ed91b762ddbd2c8e6d1`. No schema/payload adjustment or permission change followed the401. Provider acceptance of the count schema remains unverified because authorization was refused.

## Narrow real enrollment

`scripts/task52b_readiness_enrolled.py` uses the existing validators and Q4A O_EXCL/O_NOFOLLOW/file+directory-fsync writer in a **new readiness-only directory**, outside the original324-file evidence inventory. It never opens the inference journal writable, creates an application grant or changes the historical halt. The old `ReadinessTransport`/inference constructors remain closed; normal application startup/images do not import this explicit operator entry.

The exact reviewed `_SingleDial` class is reused verbatim with AST-equality coverage. Directly importing the old inference module correctly refused its frozen Q4C source identity; that guard remains unchanged. The separate readiness port imports no inference runtime. It exposes only indexed GET/count requests with fixed api.openai.com:443 paths and frozen POST bytes, verified TLS/hostname, no redirects, proxy/netrc, alternate-address retries or arbitrary HTTP operation.

`task52b_run_readiness_once` binds the exact manifest, source/writer/CA/interpreter/bootstrap identities and one fixed operation ID. A supervisor claim, scope consumption and per-operation wire consumption survive process replacement; each exact INTENT is durable before a dial. Count delivery additionally revalidates the immutable successful GET. One60-second supervised child enforces20-second operation limits,100KB request/64KB response bounds and disables core dumps. Unsafe TLS key logging is refused. Software restart does not mint a new operation ID or clear a consumed file.

Only the existing replacement-key file was used. Owner,mode0600,regular/single-link/inode/size/mtime, metadata hash/project/Read-only profile and expiry were checked before use. The loader reads only the first OpenAI dotenv line; Anthropic/Gemini lines and Google ADC are not read or exported. No secret is copied into a new file, environment, command, log or evidence. Request evidence contains identity/digests, never Authorization headers. Response credential echoes are refused without persisting echo bytes. Key material remained in the short-lived child and went only to the approved HTTPS origin.

## Durable result and boundaries

Operation `52b-readiness-owner-63ecdbb-first-v1`, build `3a7a8dd5c9c6b0272d515e742b158bb42f4d01e50e14529bf374c9f65d034517`. Private raw envelopes, validated GET, intents, consumption, loaded-code digest and terminal result/supervisor facts remain under `backend/.local/task52b-readiness/` in an owner0700 directory with13mode0600 files. Only sanitized outcomes and file/request/response hashes are committed. API request IDs remain private for possible owner support use. No private raw body or credential file enters Git.

The owner accepted AI-assisted Support's$0 counting statement for this scope. Actual billing remains independently unverified; the failed count adds no row or permission to the halted inference experiment. The API result establishes that **this restricted key was denied the count operation and the server reported missing api.responses.write**. It does not establish all projects' permission behavior, model accuracy, inference availability, current quotas, processing terms or a qualified immutable model revision. No validated input count exists, so no live cost reservation can be certified.

Final read-only checks preserve10historical paid attempts(OpenAI7/Google2/Anthropic1),$0.047366625 accounted,$11.952633375 remaining, all324private files, original hashes/source pins, five payload pairs and persistent halt. API-key/billing/financial policies, six-role deployment, images, saved-plan RLS and Qwen/model prompts remain unchanged.

## Verification

Before the live run: all existing58focused tests passed, then final57current tests(14new+43existing) plus15unchanged frozen-compatible tests passed: **72selected passes,0failures/errors/skips**. New tests cover real local TLS, exact payload/project header,401/403/redirect/truncation/timeout/framing/credential-echo/project mismatch, successful conditional count, process death at consumed/GET/POST-intent stages, replacement and competing-process exclusion, wire replay, credential identity/mode/expiry/symlink/Read-vs-Write refusals, and frozen class equality. Fake responders/keys only. Dependency consistency passed with no package changes. Source/secret-pattern checks passed before live execution; post-run key metadata/evidence modes/source/history checks passed. Full backend, full B2 replay, full SQL/Redis suites, frontend/build/images/browser were not rerun; no such pass is claimed. Public documentation was read, but no extra authenticated provider endpoint was used.

Retained preparation errors: one metadata helper used a Git option valid for only one path; direct old-module import hit the expected frozen guard; system Python lacked the existing backend dependencies. All occurred before enrollment/execution and were corrected without weakening source/TLS/financial checks. They were not live API retries. Earlier failed and passing test logs are retained with hashes in verification.

## Stop and smallest next decision

**No further API call is authorized.** Owner must explicitly decide whether to expand this same key's Responses permission toWrite (the server-named missing scope), then separately authorize a new single-count-only readiness attempt. Preserve this scope and raw evidence; never clear/reuse them. Reuse the validated GET only through a reviewed fresh/same-day evidence binding; do not automatically repeat it. Write permission is a broader API capability, not permission to run inference.

The first inference still separately requires exact purpose/security/real-writer/post-append review, fresh model/count/pricing/privacy evidence and financial/per-operation approval. Semantic review remains deferred; no diagnostic/model is certified and no remaining slot is enabled. No cloud provisioning, financial grant, public activation or Task53 occurred.
