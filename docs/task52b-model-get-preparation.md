# Task52B — separate model GET-only preparation

Baseline `128fa8ce3d10026feb78c78e693788637805b45f`. [Proposed scope](task52b-model-get-PROPOSED-v1.json), [source build](task52b-model-get-build-v1.json), [verification](task52b-model-get-verification-v1.json).

**Prepared only. No live authorization, scope, credential read or API request was created/performed.**

## Exact proposed operation

`52b-model-get-owner-128fa8c-v1`: **one GET** `https://api.openai.com/v1/models/gpt-6-luna`, empty body, existing restricted key/project `proj_E4EfEvC5uQYN4nqFaYZoo3I4`. Zero POSTs, counting, inference, retries, alternate models/credentials, permission changes, grants or cloud work. The proposed directory and private send-authorization file do not exist. No command here enrolls them.

The previous GET expired **November18,2026,00:00UTC (November17,7PM EST)**. It remains expired. Integrity checks read the original thirteen-file consumed scope without treating it as fresh evidence, changing timestamps, replaying its authorization, or passing a fabricated clock to an old validator. Original terminal count401, all consumed facts and raw/validated responses are unchanged. Both old count build manifests and the current count runner remain byte-identical.

## Reused safeguards

`scripts/task52b_model_get.py` specializes the existing fixed HTTPS adapter for only this empty model GET. It reuses exact request/response validation, single-dial TLS/hostname verification, owner-only immutable O_EXCL/O_NOFOLLOW/fsync writes and the reviewed network/capture body. A test proves that body is unchanged from the existing count adapter. No proxy/netrc, redirect, retry or general endpoint selection was added. Existing10s dial/20s request/65536-byte response limits remain.

`scripts/task52b_run_model_get_once.py` reuses the one-spawn supervisor, core-dump suppression, normalized bootstrap/source/interpreter/CA binding, exclusive launcher and worker claims, parent/worker/wire-code checks, durable consumption and INTENT before the approved key loader can run. Absent owner authorization stops before any claim or credential access. Unknown sends, interrupted workers and failed responses never become reusable scopes. New authorization, when separately approved, must itself be fresh under the same UTC-day/24-hour maximum and be rechecked after TLS before HTTP.

Credential preparation checks the existing project/file identity, owner-only permissions, expiry and unchanged original receipt containing **List models: Read**. The historical Responses Read label is not asserted as current; the existing separate Write dashboard record remains untouched. GET-only authority does not require using or refreshing a Write receipt, and does not relax any count runner gate. Actual server permission/model access remains untested until the separately approved GET.401/403 or any unexpected metadata stops permanently.

Only a future successful authorized GET could create new model evidence, bound to its own scope/INTENT/source/raw response. Freshness would be **min(observed response time+24hours, next UTC midnight)**; future timestamps and cross-day continuation refuse. No new observation or expiry is invented now. The old GET deadline is not extended. A successful refresh would not automatically replace the count runner's original evidence binding or authorize a POST; that requires separate reviewed binding and owner authorization. Model visibility is not qualification or an immutable model revision.

## Verification

**101current-source tests passed (37.027s),15frozen-compatible tests passed (1.944s); final failures/errors/skips all0.** New16cases cover exact GET/model/project/body, no POST/inference authority, response/error validation, loopback TLS/hostname/framing/redirect/timeouts, same-UTC-day/24h limits, actual spawned supervisors/workers, competing runners, crashes before/after INTENT/response persistence and replay refusal. Existing count/readiness/provider cohorts remain passing.

The initial16-case run had1error: reporting an oversized synthetic response record attempted a bounded reread that correctly refused, escaping before the stopped result was persisted. The new GET path now records that evidence refusal terminally and retains consumption; no bounds, safety checks or retries changed. Initial failure log retained. This was offline and did not touch original evidence.

Read-only journal/private-set/source checks before/after, unchanged original GET/count pins, dependency consistency, diff and credential-pattern checks passed. Ten historical attempts(OpenAI7/Google2/Anthropic1),$0.047366625 accounted,$11.952633375 remaining,324private files,five frozen pairs and persistent halt remain unchanged. No credential value was read; configured-value comparison scanning was not run for that reason. Full backend/B2/SQL/Redis, frontend/browser/build/images and live provider checks were not run or claimed. Handbook17 updated,14/15 reviewed unchanged, all20preserved.

## Exact remaining authorization

Owner must separately authorize: **“Exactly one GET /v1/models/gpt-6-luna under scope52b-model-get-owner-128fa8c-v1 using the existing WhereTo Model Evaluation key/project; no POST, counting, inference, retries, permission changes or other API request.”** Only afterward may an actual owner-only scope and authorization be enrolled, bound to this build, original evidence inventory and existing credential identity. Revalidate all prerequisites at execution. This preparation grants nothing and never runs automatically. No Task53 or deployment.
