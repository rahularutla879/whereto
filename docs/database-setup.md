# Task 47 — Supabase PostgreSQL setup

Status, October 30, 2026: **in progress; authenticated PostgreSQL verification pending**. The owner created `whereto` in organization `Where To` (Free), East US / North Virginia (`us-east-1`). Authenticated dashboard inspection independently confirmed Free, region and Healthy status. Repository preparation is implemented; simulated tests are not hosted verification. No schema, migrations, application records or persistence are implemented.

## Confirmed project and local setup

The account-creation steps below are retained for future fresh setups; the owner has already completed them and does not need to repeat them.

- Session pooler: `aws-0-us-east-1.pooler.supabase.com:5432`, database `postgres`.
- Exact username was retrieved from authenticated Connect → Direct → Session pooler → Connection parameters and saved only in the ignored backend configuration.
- `backend/.env.database` exists with mode `0600`; `backend/.local/` has mode `0700`. The existing template was used without changing Google/Ollama or frontend environment files.
- Public CA downloaded over verified HTTPS from the dashboard-linked `https://supabase-downloads.s3-ap-southeast-1.amazonaws.com/prod/ssl/prod-ca-2021.crt`, stored as ignored `backend/.local/supabase-ca.crt` (mode `0600`). It parses as one CA and contains no private key. An unauthenticated PostgreSQL SSL negotiation verified the pooler hostname and CA chain using TLS 1.3. This pre-authentication check is not authenticated database success.
- No approved credential integration, password-manager CLI or existing database password was available. The owner must enter the database password through the private local prompt. Any required password reset is performed by the owner in the dashboard; the agent does not change credentials. Password entry is stored using shell-safe quoting.

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

## Task 48 handoff, after Task 47 passes

Record confirmed project name, Free plan, region, date, chosen endpoint method and real read-only check result in HANDOVER.md and mark Task 47 complete only then. No secrets belong in that record. Until then Task 48 is blocked on this verification, not started.

Task 48 will implement the initial schema for plans, constraints, generated itineraries, itinerary stops and source metadata. Preserve simple extension points for mandatory/flexible stops, named destinations, ordered visits, origins/destinations, optional returns, durations and journey deadlines. Do not pre-design advanced tables or implement interpretation/routing/optimization from Tasks 50A–50E now. Review provider content retention rules before persisting source data. Database provisioning alone does not implement saved plans or security policies.

## Official references checked October 30, 2026

- [Connection methods and IPv4/IPv6](https://supabase.com/docs/guides/database/connecting-to-postgres)
- [PSQL and certificate verification](https://supabase.com/docs/guides/database/psql)
- [SSL enforcement](https://supabase.com/docs/guides/platform/ssl-enforcement)
- [Regions](https://supabase.com/docs/guides/platform/regions)
- [Organization billing and Free allowance](https://supabase.com/docs/guides/platform/billing-on-supabase)
- [Psycopg installation](https://www.psycopg.org/psycopg3/docs/basic/install.html)
