# Task 52B Q4C — signed offline continuation, version 1

Implementation **`52b-q4c-signed-real-schema-OFFLINE-v1`**, baseline clean `b72dfa515ef5fba644fe0715c62ccad45bce1b67`. [Concrete build/source identity](task52-q4c-build-v1.json), [verification evidence](task52-q4c-verification-v1.json). This is an OFFLINE implementation, not a live build, real trust enrollment, financial grant or model qualification.

## Components and activation limits

- `scripts/task52_q4c_auth.py`: detached Ed25519 OpenSSH verification, strict signed-envelope parsing and six role contracts. There is **no signer or enrollment issuer** in this module. A verified fact always has `execution_authorized=false`.
- `scripts/task52_q4c_protocol.py`: only factory-created temporary **synthetic** SQLite databases with exact Q4B historical DDL, signed scope/operation/review facts, immutable anchors, accounting, common lock and a closed fake transport. No caller-specified writable database constructor.
- `scripts/task52_q4c_identity.py`: exact manifest digest allowlist. Bind current B2 source set, Q1/Q3/canonical schema/scorer/clock/prompt/model and original root/ten rows/corrections, plus exact five source/payload/rubric hashes and the new implementation sources. The local `/usr/bin/ssh-keygen` binary digest is pinned; an OS update requires build review, never an automatic fallback.
- `backend/test_task52_q4c.py`: disposable synthetic owner/reviewer/operator keys and signing helper, genuine local signature tests, exact-schema attacks, fake outputs and forked-process recovery/locking tests.

Q4A/Q4B and all historical manifests remain unchanged. New implementation identity does not claim exact historical Python environment reproduction or overwrite Q3's null future-live-build sentinel. The original evaluator still refuses B2. No public endpoint, application import, environment activation, CLI, live HTTP client, provider credential loader, SSH agent, personal `.ssh` read, real journal writer or actual approval exists. Original `live_dispatch()` still always refuses. A cryptographically valid Q4C packet cannot authorize real journal access or a paid send.

## Canonical signed envelope

Protocol `52b-q4c-envelope-v1`, audience **`52b-q4c-OFFLINE-SYNTHETIC-v1`**, purpose `synthetic_evaluation_only`. These literals are mandatory, not environment options. A packet consists of exactly `envelope` (canonical JSON text) and `signature` (detached ASCII OpenSSH armor). Protocol storage also checks canonical fact bytes, preventing duplicate outer-field tricks. No wire/API transport is introduced.

Signature verification covers the **exact UTF-8 envelope bytes interpreted by the protocol**. Canonicalization is explicitly repository-style JSON, **not a claim of RFC8785**: sorted keys, compact separators, ensure_ascii=false, allow_nan=false; no trailing newline/whitespace; exact byte round-trip required. Duplicate keys, floats, NaN/infinity, non-ASCII semantic fields, unknown fields, overlong strings/arrays/depth/integers reject. Bodies are ≤50,000 bytes, semantic strings≤1,000, arrays≤66, nesting≤15 and integers strictly inside signed64-bit range. Financial/token fields are exact integers, never booleans/coerced strings. Detached armor is100–4,000 ASCII characters. Hashes/nonces are64 lower-case hex; principals use bounded `q4c-` test identities. Raw source text is not normalized or signed as an invented interpretation; its original byte hashes are bound.

Common fields: version/audience/purpose/role/principal/namespace, unique scope and nonce, synthetic journal-prefix digest, issuedAt/expiresAt, explicit trust/revocation hashes, exact build/source/configuration binding, and role-specific data. UTC timestamps use exact `YYYY-MM-DDTHH:MM:SSZ`; require issued≤now<expires and lifetime≤24h. Fresh readiness additionally requires nonfuture age≤24h and the same UTC day. The original semantic clock stays `2026-11-05T15:00:00Z`; test authorization time is a separately controlled clock, not account evidence.

The immutable binding includes the full Q3 successor specification and configuration, original journal root/row/correction/private-set identities/halt, B2 reconstruction, corpus/schema/decoder/Q1/scorer/Ordering V4 and exact five source/payload/rubric identities. Signature data cannot substitute another build/model/prompt/schema/proposal/root or slot. Common synthetic-journal and scope IDs additionally bind the particular newly created fixture. Unknown/mismatched build, binary or source fails closed.

## Trust and six non-interchangeable roles

An explicit `Trust` object pins exact canonical public trust-store and revocation-document bytes by externally supplied SHA256. A packet cannot enroll its own key or replace those pins. The trust store must say syntheticOnly=true and the offline audience, and list exactly the six roles. Each role has one exact principal, Ed25519 public key and namespace. No wildcard, certificate authority, alternate algorithm, key comment/newline injection or namespace fallback. Public-key blobs are checked structurally; revoked key hashes reject before command execution. The verifier also supplies the pinned public revocation set to OpenSSH.

Namespaces begin `whereto.task52b.`:

| Role | Namespace suffix | Required data / separation |
|---|---|---|
| Owner build/financial scope | `owner-scope.v1` | Exact max5,2,500,000/attempt,12,500,000 child nanodollars, all original ceilings/caps/concurrency/retries; explicit original-halt and critical-failure acknowledgment. |
| Independent source rubric reviewer | `rubric-review.v1` | All5×24 exact source/rubric/absence judgments and both historical failure mechanisms reviewed, independent-of-author statement. Any disagreement cannot activate the scope. |
| Owner readiness permission | `readiness-permission.v1` | Exact metadata/account/count operation categories and all five payload hashes. This is permission, not proof the checks passed. |
| Trusted readiness operator | `readiness-evidence.v1` | Link to signed readiness permission; exact5 counts1–9,952 (2,048 headroom inside12k), output2000, current observed time and complete required check fields. Here all evidence is fictional. |
| One-operation execution operator | `execute-one.v1` | Exact unused slot/source/payload,12k/2k/full reservation, owner/readiness fact hashes and previous signed-review fact hash. |
| Independent response reviewer | `response-review.v1` | Exact operation/outcome/original response hashes and all24 judgments/decision. Disagree or unresolved halts, even when other fields agree. |

Owner+readiness-permission share the synthetic owner identity; rubric+response-review share the reviewer; readiness+execution share the operator. The three groups must have **different keys and different principals**. A valid owner signature cannot stand in for a reviewer or operator. Each verification explicitly selects the expected role/principal/namespace; envelope claims are not authority.

Verification executes only `/usr/bin/ssh-keygen -Y verify` with explicit temporary **public** allowed-signers/signature/revocation files, canonical bytes on stdin, no shell, no SSH agent/user configuration environment, bounded timeout and discarded stdout/stderr. Errors/timeouts reject without retries or weaker checking. `check-novalidate` is never used. The installed `ssh-keygen(1)` interface and real local sign/verify operations were checked; no remote SSH connection occurs.

**Trust limitation:** tests generate all three keys under one local OS account, only in private temporary directories. The signing helper exists exclusively in the test module; private keys never enter Git/configuration/experiment storage and are cleaned afterward. Different keys prove cryptographic role separation, **not different real humans, semantic competence or independent review**. Trust pin authenticity, current revocation snapshot, protected clock/files/code and key enrollment must be supplied by a separately approved operator boundary. Arbitrary same-UID Python/admin code is outside this prototype's isolation guarantees. No real principal, key or signing authority is enrolled here.

## Exact-schema append-only sequence

New synthetic databases use the **exact original metadata/attempts DDL** with no migration or extra SQL table. Only original consumed slot IDs and real status labels are mirrored. Root/records/charges are clearly fictional (default10×1,000,000 nanodollars), **not copied historical paid rows** or a second allowance. Original real root/row hashes are separate signed compatibility evidence. The signed envelope also binds each synthetic root/prefix. An in-process fixture registry, private0700 directory, no symlinks/hardlinks and fixed synthetic name prevent accidental writes to the real evaluation directory. Unregistered/restarted-process state refuses; explicit forked test children inherit only the fictional capability. This is not OS sandboxing.

Under one nonblocking `experiment.lock` EX lock:

1. Verify build, exact schema, complete original synthetic prefix/root, original halt, every row/slot/status/charge, fact chain, source identities, signed four-part scope and current readiness.
2. Verify one-operation permission, exact next Q3 slot, parent/review hashes, nonce unused across **all** roles, all original and child attempt/exposure limits. Scope approval alone cannot admit an operation.
3. Exclusively create/fsync START, including signed permission and expected next monotonic rowid/operation identity. No automatic recovery if this start is incomplete.
4. `BEGIN IMMEDIATE`; INSERT one immutable `reserved_uncertain` full2,500,000 anchor using ordinary SQLite rowid. FULL-sync commit before intent. Never UPDATE/DELETE/refund an anchor, root or old halt. Old Ledger reserve/finish are not called.
5. Create/fsync immutable INTENT bound to START and payload, then exactly one closed fake exchange. No transport callbacks, live fallback or retry.
6. Append immutable OUTCOME with complete response/hash, raw/B2/V4 assessment, usage-based liability and full fake-exchange duration. Preserve reservation; exposure is max(anchor, larger observed liability). Critical raw error/provider error/uncertainty/overrun halts, even if Ordering V4 safely blocks it.
7. Require a separate cryptographically valid reviewer packet tied to the outcome/response and all24 fields. Store REVIEW append-only under lock. Disagreement/unresolved halts and independently blocks progression even if a halt file were missing. Only then is the next exact unused slot eligible. No next batch after five.

Financial admission validates every non-null provider/case/repetition, allowed status, integer nonnegative charge, unique slot, contiguous expected row identities and complete immutable prefix. SQLite does not enforce these itself. Deleted/reused highest row IDs cannot erase the durable START/intent/outcome history; mismatches refuse. Original+child counts/exposure are used, not only successful responses. Unknown rows/scopes/facts refuse, never create a fresh allowance. Unknown source-to-effective mappings stop through the unchanged Q4A assessment. Fake positive output remains an authored fixture, not a model success or independently correct result.

Fixed slots remain **extension-repeated/r2 → journey-04/r2 → extension-partial/r2 → journey-06/r2 → journey-21/r1**, same model/v4 prompt/19 examples/schema/Q1 rubric/scorer and B2 runtime. Limits remain $12/594/198/12k/2k/concurrency1/retries0; fictional child5/$0.0125. The real experiment still has no new approval/reservation/attempt.

## Recovery and threat-model limits

START/reservation/INTENT/OUTCOME/REVIEW are independently durable; SQL and files are not one transaction. Missing/uncertain state blocks, never implies permission to resend. A committed anchor stays spent even when no fake send happened. A pre-commit crash can roll back SQL only in the **fictional** database while the durable START blocks automatic retry. An outcome missing review blocks. A lost response is not recovered by another model call. Old and child terminal halts survive restart. A crash before any durable START has no admitted operation and no automatic restart.

Tests terminate real child processes at seven boundaries and compete with a separate process lock. They demonstrate local process-termination/SQLite rollback/fsync ordering, **not power-loss, malicious OS, distributed durability or protection against coherent rollback/deletion of all local audit state**. Those require protected operator storage and possibly an independently anchored monotonic audit checkpoint. No real journal write/recovery was performed. Signatures alone do not supply single-use semantics; the protected durable fold does.

## Review status, real boundary and stopping condition

All real review packages remain blank. Five selected24-field rubrics and both historical failure mechanisms still need independent external review; each actual future response needs separate review before another operation. Six global Q1 judgments,66 gold approvals and historical response signoffs remain broader qualification blockers. Seven historical OpenAI outputs retain actual v3/v4 identities and classifications: journey-07 stays an insufficient-provenance rejection; extension-repeated stays an accepted critical error, while offline V4 rejects the unsupported0→1 and preserves1→2. No raw response or historical score is repaired.

Q4C completes the **offline verifier and synthetic exact-schema protocol**, not actual enrollment or live integration. Next bounded approval checkpoint: review this build/envelope/trust/recovery design and arrange independent rubric review; separately approve protected real owner/reviewer/operator enrollment and a same-original-journal adapter integration tested offline. A real implementation needs protected trust pins/revocations/clock/code/audit state, a reviewed non-synthetic purpose/build, all-scope real row/outcome folding, and explicit activation controls that preserve the old halt. Current Q4C has no flag to enable those. Only after those gates could separately authorized fresh provider readiness and exact paid scope be considered.

No provider/count/metadata/account/Maps request, real SSH key access/enrollment, billing/credential/quota/IP change, production model/V4/shadow change, hosted state/infrastructure/migration or Task53 work. Gemini HTTP400/IP and Anthropic grammar compilation remain BLOCKED.
