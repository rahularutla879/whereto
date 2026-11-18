# Task52B — authorized GET attempt stopped, scope consumed

Execution source `37bb5d2eb878670be521a2b9795c5cb691b978ab`, pinned build `b41fc246489612e6c1714068f7957363ad8e139bd3ee08398cd1630ef95e10fb`. [Sanitized outcome and verification](task52b-authorized-model-get-result-v1.json).

**No HTTP result or fresh model evidence was obtained. No retry occurred.**

The owner explicitly authorized one supervised GET `https://api.openai.com/v1/models/gpt-6-luna`, existing restricted key/project `proj_E4EfEvC5uQYN4nqFaYZoo3I4`, scope `52b-model-get-owner-128fa8c-v1`. After passing preflight, owner-only scope and authorization were enrolled with source, original evidence, credential identity and explicit approval hashes. The approved loader read only the existing OpenAI line inside the core-dump-disabled worker. No credential value was printed, copied to evidence, exported, changed or committed.

Exactly one supervised attempt ran. Durable launcher/worker consumption, INTENT and wire claim exist. Capture at `2026-11-18T01:22:46.247299+00:00` records **status null, complete false, errorCategory Refused, sendStarted false, zero body bytes**. No HTTP transmission beginning or provider response was recorded. The runner conservatively returned `uncertain_or_incomplete_no_retry`; both scope and wire authorization remain permanently consumed. This is not HTTP401, a model rejection, or a successful connectivity/model check. Validated model and new expiry are absent. The old GET remains expired at its unchanged November18,00:00UTC deadline.

## Immutable evidence

Ten owner0600 files under ignored `backend/.local/task52b-readiness/52b-model-get-owner-128fa8c-v1/` retain scope, launcher/runtime/supervisor facts, consumption, INTENT, wire claim, incomplete capture and terminal result. Separate owner0600 `.send-authorization.json` alongside the directory records the actual owner approval. Parent directories are0700. File hashes, scope/auth hashes and the captured empty-body hash are in the sanitized result; no private raw files or credential bytes entered Git. No fact was overwritten, removed or reset.

## Local refusal investigation — no further network

A single fictional probe disabled sockets and substituted an in-memory dialer. It reproduced **unstable wire-code serialization**: `marshal.dumps(GetOnlyHTTPS.exchange.__code__)` hashes to `e427db367dd903016b459a29061f2e10e6d967ab68daa5d24303f89321f770b1` at the first check, but `637a6d02125ea03450ab5b3d2f5688641735ab9afe0186591c642e89bbabaf85` after the function establishes local references. The actual stored runtime hash matches the first. The second full-code check can therefore refuse an unchanged function before HTTP transmission. The live record intentionally contains only the generic Refused category; its exact refusal branch was not captured, so the reproduction is not conclusive historical branch attribution.

The source and guard remain unchanged. This checkpoint does not remove identity checks or retry the send. The existing tests substituted provider exchanges in supervisor tests or skipped real supervision in loopback fixtures; they did not establish that combined full-code identity remains stable during the actual supervised exchange. Repair requires a stable fingerprint preserving full code/constant coverage and an integrated supervised-transport offline regression, not merely weakening/removing the check.

## Verification and preserved boundaries

Before the attempt: **101current-source tests and15frozen-compatible tests passed**,0failures/errors/skips; source/runtime/CA/credential-stat/private-mode and targeted secret-pattern checks passed. Afterward: original historical/private/journal/source integrity and all ten new immutable-file checks passed. The no-network probe is diagnostic evidence, not a successful provider test. Full backend/frontend/SQL/Redis/container suites were not run and are not claimed.

Original ten attempts(OpenAI7/Google2/Anthropic1),$0.047366625 accounted,$11.952633375 remaining,324private files,five frozen pairs and persistent halt are unchanged. Original thirteen-file readiness scope and the old expired GET are intact. No token counting, inference, retry, key/permission/billing change, financial grant, cloud provisioning or Task53 occurred. This scope cannot be reused even though the capture records no HTTP start. Count authority remains absent; no evidence binding was silently updated.

**Stop.** The next action is an offline-only identity-fingerprint correction and integrated regression; any later live GET needs a new scope and new explicit owner authorization. No new live authorization is inferred from this failed attempt.
