> Current Task 50 security audit and acceptance: [safe database access](database-security.md). Earlier task-pending statements below are historical.

# Supabase PostgreSQL setup — Tasks 47–49

Task 49 is complete: use the separate restricted runtime configuration and commands in [enable explicit saving locally](#task-49-enable-explicit-saving-locally). Historical administrator connectivity instructions below are for checks/migrations, never runtime startup.

Task 47 checkpoint, October 30, 2026: **complete; actual authenticated read-only PostgreSQL verification passed**. The owner created `whereto` in organization `Where To` (Free), East US / North Virginia (`us-east-1`). Authenticated dashboard inspection independently confirmed Free, region and Healthy status. The real `backend.database_check` returned exit code 0 after DNS resolution, authenticated SELECT, a confirmed read-only transaction, verified client-to-pooler TLS and clean connection closure. At that checkpoint no schema, migrations, application records or persistence were implemented.

Task 48 subsequently applied and verified the initial private schema. The Task 47 evidence below describes the earlier connectivity-only checkpoint. For current tables, migration/test commands, access protection and provider retention, read [the database schema guide](database-schema.md). Task 49 now implements saved-plan endpoints through the restricted runtime described below. Task 50 and 50A–50E remain unstarted.

## Confirmed project and local setup

The account-creation steps below are retained for future fresh setups; the owner has already completed them and does not need to repeat them.

- Session pooler: `aws-0-us-east-1.pooler.supabase.com:5432`, database `postgres`.
- Exact username was retrieved from authenticated Connect → Direct → Session pooler → Connection parameters and saved only in the ignored backend configuration.
- `backend/.env.database` exists with mode `0600`; `backend/.local/` has mode `0700`. The existing template was used without changing Google/Ollama or frontend environment files.
- Public CA downloaded over verified HTTPS from the dashboard-linked `https://supabase-downloads.s3-ap-southeast-1.amazonaws.com/prod/ssl/prod-ca-2021.crt`, stored as ignored `backend/.local/supabase-ca.crt` (mode `0600`). It parses as one CA and contains no private key. An unauthenticated PostgreSQL SSL negotiation verified the pooler hostname and CA chain using TLS 1.3. A subsequent authenticated `backend.database_check` also passed; both results are recorded separately.
- No approved credential integration, password-manager CLI or existing database password was available. The owner entered the database password through the private local prompt; the authenticated check then passed. Any required password reset is performed by the owner in the dashboard; the agent does not change credentials. Password entry is stored using shell-safe quoting.

## Owner dashboard steps

1. Open <https://supabase.com/dashboard> and sign up or log in using your own account. Complete email/account verification privately.
2. Select an organization you own on the **Free** plan, or create a Free organization. Billing is organization-wide: a project in a paid organization inherits that plan. The published Free allowance is two active free projects across organizations where you are an owner/admin. If unavailable, stop rather than upgrading or deleting another project.
3. Select **New project** and name it `whereto` or `where-to`.
4. Generate a strong, unique database password and save it in your password manager. Never send passwords, authenticated connection strings, access tokens or privileged keys in chat.
5. Provisional recommendation: **East US / North Virginia (`us-east-1`)** if we expect a US East backend serving the current US-focused prototype. Hosting has not been chosen. Prefer a region close to the future FastAPI server and users, considering data residency. Your physical location alone does not decide this. Confirm the actual selected region in the dashboard; a general region grouping may select a different specific region.
6. Confirm the organization is Free, keep paid add-ons off, and create the project. Do not enter payment details, subscribe, upgrade or buy IPv4 for this task. Wait for provisioning to finish and the project to show ready/healthy. Supabase itself provisions system schemas; this task creates no application tables.
7. Report only the project name, confirmed Free plan and region. If authentication is unavailable, the owner must perform these steps. Project creation is not delegated to an unauthenticated tool.

## Connection choice

| Method | Intended use | Task 47 decision |
| --- | --- | --- |
| Direct PostgreSQL, port 5432 | Persistent backend sessions, administrative work; default endpoint uses IPv6 | Consider in production if hosting supports IPv6; no paid IPv4 add-on |
| Shared session pooler, port 5432 | Persistent connections from IPv4 networks | Selected for this local FastAPI verification; exact host and `postgres.<project-ref>` user come from Connect |
| Shared transaction pooler, port 6543 | Transient/serverless connections; session state and prepared-statement limitations | Not selected; reassess only if backend hosting requires it |
| Supabase Data API, HTTPS | HTTP access using API keys/JWTs and access policies | Not a PostgreSQL driver connection; not needed to verify PostgreSQL or used by the app |

Next.js hosting does not determine the Python connection strategy: choose based on where FastAPI actually runs. No deployment target is currently configured. Task 48 must revisit bounded connection pooling, least-privilege runtime access and schema/migration decisions; production requires a secret store and host-specific networking review. No Supabase JavaScript SDK, service-role key, ORM or persistent pool is needed here.

## Private local configuration

All commands below run from `/Users/rahularutla/Documents/whereto` in Terminal. Keep existing Google/Ollama settings and root `.env.local` untouched. Python does not auto-load env files.

1. In the project dashboard select **Connect → Session pooler → View parameters**. Use the exact displayed host, database, port and username. Do not copy a full password-bearing URL into chat or a command.
2. In database settings locate the SSL certificate download (see the official PSQL/SSL guide below). Save the CA certificate locally as `backend/.local/supabase-ca.crt`, creating that directory if needed. Downloading the certificate is insufficient by itself: the check uses `sslmode=verify-full` and this CA file to verify the endpoint hostname.
3. Create an ignored local configuration without replacing an existing file:

   ```sh
   cd /Users/rahularutla/Documents/whereto
   mkdir -p backend/.local
   (umask 077; cp -n backend/.env.example backend/.env.database)
   chmod 600 backend/.env.database
   open -e backend/.env.database
   ```

4. Edit the values privately in TextEdit as plain text. Set `WHERETO_DB_HOST`, `WHERETO_DB_PORT=5432`, `WHERETO_DB_NAME`, `WHERETO_DB_USER`, `WHERETO_DB_PASSWORD` and `WHERETO_DB_SSLROOTCERT`. The certificate value should be `/Users/rahularutla/Documents/whereto/backend/.local/supabase-ca.crt`. Keep ASCII single quotes around each value. For this simple shell file, use a password-manager-generated password of at least 32 random letters/digits to avoid shell quoting mistakes; if your existing password contains a single quote, do not paste it into this shell format without correct shell escaping. Never execute a configuration file supplied by someone else. Do not change the password just to troubleshoot a network issue.
5. Save the file and close the editor. Do not put database credentials in root Next.js env files or any `NEXT_PUBLIC_*` variable. The ignored backend env file is sourced only by the explicit command below. Database values are not needed by ordinary development startup.

The existing `.env*` ignore rule covers `backend/.env.database`; `backend/.env.example` is the only tracked backend env file. Downloaded certificates under `backend/.local/` are ignored. Verify paths without showing their contents:

```sh
git check-ignore backend/.env.database backend/.local/supabase-ca.crt
```

## Run the controlled check

Install pinned dependencies in the existing Python environment if needed:

```sh
cd /Users/rahularutla/Documents/whereto
backend/.venv/bin/python -m pip install -r backend/requirements.txt
```

Then run this subshell. Its exports disappear on exit; no password goes into command history or ordinary app startup:

```sh
(
  set +x
  set -a
  source backend/.env.database
  set +a
  backend/.venv/bin/python -m backend.database_check
)
```

The checker validates settings before networking, resolves the endpoint, opens one authenticated session with `verify-full`, requires client-to-pooler TLS, begins a read-only transaction, applies a transaction-local five-second statement timeout, executes `SELECT 1, current_setting('transaction_read_only')`, then rolls back and closes. Connection timeout is 10 seconds per address; query timeout is five seconds. It neither creates objects nor runs migrations, writes records, contacts Google/Ollama, nor imports the web application. No retries are implemented in application code. Transaction settings are local to this transaction; the checker does not change database-wide, role-wide or pooled session defaults. DNS resolution uses the OS resolver and can take longer than the connection timeout.

Success prints only a fixed message confirming DNS, authenticated SELECT, read-only transaction, verified client-to-pooler TLS and closed connection. A missing setting, bad certificate, DNS/auth/network/query failure returns exit code 1 and a fixed error without raw driver output. Check readiness, exact Session pooler parameters, local outbound connectivity and CA path privately. Never disable certificate verification to work around a failure.

This TLS observation verifies the client-to-pooler leg; it does not independently inspect the pooler's internal connection to PostgreSQL. Do not infer end-to-end internal transport guarantees from it. Ordinary FastAPI `/health` and Next.js `/api/health` intentionally do not test the database.

Offline regression tests: `backend/.venv/bin/python -m unittest backend.test_database_check -v`. Missing-config check: `backend/.venv/bin/python -m backend.database_check` in a Terminal with no database variables exported. Neither substitutes for an actual hosted check.

## Historical Task 48 handoff — Task 47 passed

Confirmed project, Free plan, region, session-pooler method and actual successful read-only result are recorded in HANDOVER.md. Task 47 is complete. No account/configuration blocker remains for this connectivity check. Task 48 is not started and requires its own task authorization; no secrets belong in the handoff.

Task 48 will implement the initial schema for plans, constraints, generated itineraries, itinerary stops and source metadata. Preserve simple extension points for mandatory/flexible stops, named destinations, ordered visits, origins/destinations, optional returns, durations and journey deadlines. Do not pre-design advanced tables or implement interpretation/routing/optimization from Tasks 50A–50E now. Review provider content retention rules before persisting source data. Database provisioning alone does not implement saved plans or security policies.

## Official references checked October 30, 2026

- [Connection methods and IPv4/IPv6](https://supabase.com/docs/guides/database/connecting-to-postgres)
- [PSQL and certificate verification](https://supabase.com/docs/guides/database/psql)
- [SSL enforcement](https://supabase.com/docs/guides/platform/ssl-enforcement)
- [Regions](https://supabase.com/docs/guides/platform/regions)
- [Organization billing and Free allowance](https://supabase.com/docs/guides/platform/billing-on-supabase)
- [Psycopg installation](https://www.psycopg.org/psycopg3/docs/basic/install.html)

## Task 49: enable explicit saving locally

The runtime must **not** use `backend/.env.database` (the migration administrator).
Task 49 adds `0002_private_saved_plans.sql` and a separate, restricted login. The
migration is already applied in the authorized development project. Data API
remains disabled. To provision a fresh development project after applying the
versioned migrations, source the administrator file only in a subshell and run
`backend/.venv/bin/python -m backend.persistence_setup`. This creates a new,
ignored `backend/.env.persistence` with mode 0600 and a random password; it never
overwrites/rotates an existing file or prints secrets. Keep both configurations
private. The runtime login has schema USAGE and SELECT/INSERT on the five product
tables only, capability-scoped RLS, no membership in administrative roles, no
ledger access, DDL, UPDATE or DELETE. The migration administrator can explicitly
SET ROLE to that restricted identity for rollback testing. API roles retain zero
schema/table grants. Runtime identity is checked on every connection.

From `/Users/rahularutla/Documents/whereto`, start the backend in a Terminal:

```sh
(
  set +x
  set -a
  source backend/.env.persistence
  set +a
  VENUE_DATA_MODE=mock npm run dev:backend
)
```

In a second Terminal in the same folder run `npm run dev`. This loads database
credentials only into Python. Keep all Google development flags unset. Ordinary
`npm run dev:backend` still generates mock plans without database configuration;
Save Plan then reports unavailable and leaves the generated cards intact.

Describe coffee and a museum in Baltimore on a future date; choose Surprise Me;
generate, select an option and click **Save Plan**. Refresh: the last saved plan
opens automatically in a separate saved-plan section, preserving every saved
option, selected option, ordered activity/stop and normalized constraint. Copy the
private link from **Your private link** before clearing browser storage. To open
another link, use **Reopen a saved plan**. No dashboard or account is required.
Only one immutable save is supported per generated receipt. More-options responses
issue fresh receipts; each saved page contains at most three options.

See [saved-plan architecture and limitations](saved-plans.md). Hosted integration
fixtures are opt-in and rollback-only:

```sh
(
  set +x
  set -a
  source backend/.env.database
  set +a
  WHERETO_DB_SCHEMA_TESTS=1 backend/.venv/bin/python -m unittest backend.test_database_schema backend.test_saved_plans -v
)
```

These admin-run fixtures impersonate the restricted role within a rollback-only
transaction; they make no Google calls and leave no plans behind.

## Acceptance correction: administrator configuration versus runtime configuration

`backend/.env.database` is the migration/checker identity. It was the cause of the
owner's failed save startup: its variables were present and authenticated, but the
application correctly refused the privileged identity. A successful connection
checker alone does not establish that saving is configured with the runtime role.

Use the existing **`backend/.env.persistence`** for runtime startup. There is no
need to recreate Supabase, change a password, rerun provisioning, or change grants.
From `/Users/rahularutla/Documents/whereto`, stop FastAPI with Control+C, then use:

```sh
(
  set +x
  set -a
  source backend/.env.persistence
  set +a
  VENUE_DATA_MODE=real WHERETO_REAL_DEV=1 WHERETO_ENV=development WHERETO_START_LOOKUP_DEV=1 npm run dev:backend
)
```

This retains the existing real-mode development path and manual starting-place
lookup. Keep any other already authorized local development switches you normally
use; no quota, billing, credential or model change is part of this fix. Planning
in real mode makes Google requests when **you intentionally submit**; acceptance
tests used offline provider responses instead. For mock mode, use the earlier
mock startup command with this same restricted configuration.

For compatibility with the owner's administrator-loaded startup, application
persistence now selects the existing private runtime file safely whenever a
`postgres.*` environment is loaded. It still refuses administrator SQL and checks
`current_user` after connecting. The source environment is not mutated. If the
private runtime file is missing, insecure or invalid, saving fails with an
explicit runtime-configuration category instead of silently broadening privileges.


## One-command owner startup — current acceptance refinement

The current owner workflow is `npm run dev:backend`, followed by `npm run dev` in the second Terminal. It loads the ignored owner profile and restricted persistence file automatically; the earlier manual sourcing commands remain historical alternatives. Explicit mock override: `npm run dev:backend -- --mock`. TLS, runtime identity, grants, RLS and migrations are unchanged.

[Exact architecture, evidence rules, fields, billing, limits and verification](acceptance-refinements.md).


## November 1 — final Tasks 46/49 acceptance repair

Current behavior supersedes earlier automatic/all-option saved-view descriptions: normal visits keep saved links collapsed, explicit private links render only the selected detailed itinerary, and Open saved plan opens a secure new tab. One explicit selected-stop detail load uses the existing Pro mask with Maps URI; optional phone/website fields require deliberate existing Enterprise contact opt-in. Provider content stays in memory. Structured continuation states distinguish combinations, discovery, bounded exhaustion, limits, constraints and pending routes; ranking is preserved. Actual default-port startup was checked, and occupied backend ports now give actionable guidance. No migration, role/RLS/TLS/quota change or later task. See [the final repair report](final-acceptance49.md) and the latest HANDOVER.md evidence.

## Current saved-detail/performance acceptance

No migration, grant, RLS, role, TLS or connection change is needed for these fixes.
The same owner-only restricted runtime profile supports save/reopen; current Google
details are never inserted in PostgreSQL. AI readiness has no database access.
Hosted tests use rollback fixtures; committed browser fixtures are cleaned up only
by their separately recorded capability hashes, preserving every owner plan.
See [latest acceptance evidence](saved-details-performance49.md).

## November 1 sharing/UI verification

No database configuration, role, RLS, TLS or migration change was needed. Hosted35/35 checks (18 real PostgreSQL rollback cases plus17offline) and restricted-login authenticated TLS verification passed. The browser committed one invented selected-option fixture; only its exact hashed plan was removed, with independent committed-cleanup verification. Owner plans were preserved. Ordinary `npm run dev:backend` and explicit mock startup both passed. [Current sharing limits and UI evidence](sharing-ux49.md).
