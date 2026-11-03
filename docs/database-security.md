> Current Task 50E: approved local website and version 2 saving integration is implemented. Initial milestone descriptions below are historical; see [current flow, gates and limits](advanced-integration.md).

# Task 50 — safe database access

November 2, 2026. Scope: existing anonymous local-development Supabase persistence only. Acceptance: preserve legitimate saving/reopening and selected refresh; deny cross-capability access and malformed requests; retain least privilege, verified TLS, atomic/idempotent writes and credential-free errors; pass offline, hosted and browser checks. Tasks 50A–50E and 51 are unstarted.

## Audit and changes

| Area | Existing protection confirmed | Task 50 action / qualification |
| --- | --- | --- |
| Connection | Supabase shared session pooler, port 5432; explicit CA, `sslmode=verify-full` | Preserved. Five-second runtime connect/statement and two-second lock timeouts. No transaction-pooler switch. |
| Runtime identity | Separate `whereto_plan_runtime` login; exact `current_user` checked on each connection | Preserved; authenticated directly in hosted tests, rather than relying only on admin `SET ROLE`. |
| Administrator | Ignored private admin file used only by explicit checker/migration/test commands | Never connected as admin by application requests. Admin-loaded legacy startup selects only the private restricted file; missing/unsafe runtime settings fail closed. |
| Files/configuration | Owner-only, regular, nonsymlink runtime files; allowlisted data-only parser; ignored CA and configuration | Preserved without editing private files. Next build/start now refuses public database environment names, without printing values. No `next.config.env` secret injection. |
| Ownership/grants | Administrator owns all six tables; nonowner runtime has schema USAGE + SELECT/INSERT on five product tables only | Hosted catalog verifier passes forced RLS, ownership and exactly 11 nonowner grants; API roles and PUBLIC have no product access. Added runtime role-membership drift check. |
| RLS | Five capability/ancestor policies; expiry enforced on root row; forced RLS on all six tables | No policy or grant change. Empty/wrong capability returns zero accessible rows. Runtime cannot update, delete, disable RLS, create roles/tables or access migration ledger. |
| Migrations | Separate explicit CLI; trusted numbered SQL; checksums, transaction advisory lock, atomic application | Both existing migration files and ledger unchanged. Runtime has no migration API/ledger privileges. |
| Links | Two independent 256-bit random receipt/access tokens; constant-time verifier comparison; SHA-256 access verifier in PostgreSQL | Preserved; exact 43-character request length added alongside syntax validation. No account/ownership claims accepted. |
| Expiry/authorization | 30-day DB expiry; missing/expired/inaccessible all return 404; no listing or UUID retrieval API | Two actual committed test plans prove token substitution/cross-record access denied. Valid sharing and selected option survive. |
| API input | Typed extra-forbid models, receipt-owned data, maximum three options/four stops, canonical activity/travel/date constraints, 4096-byte streamed body limits | Reject duplicate JSON keys, nonfinite constants, nonobject/malformed JSON before typed parsing. Proxy malformed JSON now returns 422 instead of 503. Size/denial responses also carry no-store/no-referrer. |
| Stored validation | Reconstructed document revalidated on open, including order, membership, source mode and dates | Added provider-ID syntax and retained-location/origin validation. Nested corrupt-row validation maps to the same safe 404 for reopen and refresh. Past outing dates remain readable until link expiry. Legacy null transport still means driving. |
| Provider refresh | Reopens under RLS/expiry on every action; only saved selected option, four stops maximum; client cannot supply Place IDs | Added defense before URL construction: malformed provider references fail before auth/network. Existing Pro/explicit Enterprise gates and replay/shared admission preserved. DB connection closes before provider work. |
| Writes | Parameterized values; SQL identifiers from internal constants; five-table atomic transaction; FK/uniqueness/check constraints | Preserved. Capability-scoped advisory lock serializes duplicate saves. Same fingerprint is a no-op; changed content conflicts. Failure rolls all inserts back. No automatic write retry. |
| Lifetime/errors | Fresh connection per action, four-slot nonblocking admission, Psycopg context commit/rollback/close | Failure-stage and cleanup regressions cover connect, query and uncertain commit errors. Fixed error codes distinguish DB outage from unavailable link; raw exceptions excluded. |
| Browser/logging | Fragment capability cleared from URL; body-only fixed-path POST proxy; no-store/no-referrer; no analytics integration | Preserved. Local development launcher disables access logging; failure evidence records only fixed category, correlation ID, operation and exception type. Do not enable body logging/tracing of capabilities. |

No database migration was needed. There is no data rollback step: revert application code if necessary; preserve both migration checksums and all existing data. Disposable hosted tests delete only their generated capability hashes, with independent committed absence checks. Existing nonexpired records are inspected read-only without printing contents.

## Connection investigation

No historical root cause is established. Current hosted concurrency, repeated fresh reads, duplicate writes and fresh-process reopening pass. A deterministic test terminates **only its own actual PostgreSQL session**, confirms a safe `database_connection_failed` response, then successfully reopens the same committed plan on a new connection. Offline failures at connect/query/commit verify one attempt and admission release; a fifth simultaneous connection is refused while four are held.

Supavisor substitutes protocol metadata: `connection.info.backend_pid` is synthetic and `application_name` can be `Supavisor`. The first diagnostic tests incorrectly expected the supplied application name and targeted the synthetic PID; those assertions failed and were corrected. Interruption now obtains `SELECT pg_backend_pid()` inside its own transaction. PostgreSQL GRANT by a nonowner may warn/no-op rather than raise; the corrected probe checks effective denial and always rolls back. These are test-harness findings, not proven historical application defects.

There is no application connection pool or cached stale session to reuse. Session-pooler capacity/network/project availability, DNS, TLS handshake and credentials can still fail. Client-to-pooler certificate/hostname verification is retained; this does not independently certify the pooler's internal transport. No unbounded retries, relaxed TLS or admin fallback were added. An uncertain commit must be reconciled by reopening or resubmitting the **same token/selection**, never inventing a new save automatically. Receipts remain process-local and expire after ten minutes; restarting requires regeneration for a previously unsaved receipt, while committed links remain readable.

Official references: [Psycopg transaction/context cleanup](https://www.psycopg.org/psycopg3/docs/basic/transactions.html), [Supabase verified SSL](https://supabase.com/docs/guides/platform/ssl-enforcement), [Supabase RLS and privileged roles](https://supabase.com/docs/guides/database/postgres/row-level-security). Repository implementation and actual hosted checks are the evidence for this project's permissions.

## Reproduce checks

Working folder: `/Users/rahularutla/Documents/whereto`.

```sh
npm run test:backend
npm test
npm run typecheck
npm run lint
npm run build
backend/.venv/bin/python -m pip check
backend/.venv/bin/python -m unittest backend.test_database_security backend.test_saved_plans backend.test_api -v
python3 scripts/security-scan.py
```

Hosted tests use the existing authorized development project, no Google requests:

```sh
(
  set +x
  set -a
  source backend/.env.database
  set +a
  WHERETO_DB_SCHEMA_TESTS=1 backend/.venv/bin/python -m unittest backend.test_database_schema backend.test_saved_plans backend.test_database_security -v
)
```

Unlike the earlier rollback-only suite, Task 50 additionally commits disposable fixtures to verify independent concurrent sessions, process restart and connection interruption. Cleanup is registered before writes and checks only generated hashes. An externally killed test process can prevent cleanup; investigate its exact disposable records privately rather than deleting broadly. Role/GRANT and existing schema tests remain rollback-only. Do not use these commands against another project.

Offline coverage includes valid save/reopen boundaries, unavailable/expired-record short circuit, token/receipt substitution, injected IDs/privileged fields, bounds/invalid constraints/provider references, duplicate submissions, rollback/connection exceptions, four concurrent operations and admission refusal, log redaction and selected-only refresh. HTTP tests cover malformed/duplicate/nonfinite JSON, invalid tokens, oversized bodies and origin rejection. Existing fixture suites cover legacy null driving and refresh failure without provider allowance. Actual RLS/role enforcement and real transaction rollback are verified against PostgreSQL; a mock permission exception alone does not prove database authorization.

The credential scanner reads sensitive values privately and reports counts only. It checks current tracked/new files, all generated Next artifacts and historical Git objects against **currently configured** database credentials. It cannot rule out exposure of retired/unknown credentials, external logs, browser extensions or untracked backups. No exposure was identified in this audit; no password or Cloud configuration was changed. Rotate privately if separate evidence of exposure arises.

## Remaining boundaries

This is a local-development MVP. Capabilities grant access to anyone possessing the link; there are no accounts, revocation, automatic expired-row deletion or distributed abuse controls. Browser storage, clipboard/history sync and XSS/extensions remain capability risks. Database compromise/admin access remains privileged. The receipt registry and connection semaphore are process-local, not deployment-wide admission. Do not deploy publicly on the basis of this task. No account infrastructure, roadmap extension, provider/ranking/UI redesign, quota/billing change or live Google verification was introduced.

## Final verification

Full backend: 685 reported run, OK with 34 skips (26 hosted, eight opt-in lifecycle), 180.789s. Hosted suite: 56/56 (26 actual PostgreSQL + 30 offline), 27.067s. Frontend: 234/234, 116.995s. Focused security/saved/HTTP: 38 reported run, OK with 15 hosted skips. TypeScript, ESLint, production build, Python dependency consistency, exact-credential/history/Next-artifact scan and full diff review passed. The lifecycle opt-in suite was not rerun; its implementation is unchanged.

Desktop 1280 and mobile 390 actual hosted save/reopen checks passed with invented provider transports and zero Google sends. Selected option 2 reopened in a new tab; selected-only refresh loaded two synthetic venues. Mobile also saved/reopened a new option 1 and had no horizontal overflow. Two committed browser records were removed by exact test verifiers and cleanup independently verified. Screenshots: `/tmp/task50-desktop.png`, `/tmp/task50-mobile.png`. Temporary test servers/tabs were closed; pre-existing owner servers were preserved. See HANDOVER.md for detailed evidence and initial corrected test assumptions.


## Task 50E — advanced application integration

Task 50E preserves all runtime grants, forced RLS, verified TLS and capability hashing/expiry. Version 2 requirements use existing JSON preferences and positive model_version; no migration or privileged production change. Committed restricted-role persistence/restart checks and disposable cleanup are required. [Contracts, limits and verification](advanced-integration.md). Earlier task-pending statements above are historical. Task 51 remains unstarted.
