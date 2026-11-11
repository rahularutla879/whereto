# Development commands

The normal working folder is `/Users/rahularutla/Documents/whereto`. Start every Terminal session by checking the folder. Commands below are deliberately separated by their effects. Do not paste the entire page as a script.

## 1. Safe read-only orientation

```sh
cd /Users/rahularutla/Documents/whereto
pwd
git status --short
git rev-parse HEAD
git log -5 --oneline
rg --files app components lib backend scripts docs/learning
```

`cd` selects the working folder; `pwd` prints it. Status lists changes and untracked files; rev-parse prints the exact selected commit. `rg --files` lists files. It does not print private profile contents. Ignore dependency/virtual-environment output if your local ripgrep configuration differs; do not traverse secrets to learn the code.

## 2. Read a focused function or change

```sh
rg -n 'def validate_journey|def normalize_explicit_durations' backend/journey.py
rg -n 'requireOrigin|prepareSurprise' components/location-controls.tsx lib/planning-client.ts
sed -n '1,110p' backend/journey.py
git diff --stat
git diff -- README.md HANDOVER.md
git ls-files --others --exclude-standard
git show HEAD:backend/main.py
```

`rg -n` prints matching line numbers. `sed -n` prints a chosen source range. Diff shows tracked modifications, not untracked contents; explicitly read every intended new file. `git show` reads committed source. None of these commands should print credentials when limited to the listed public source/documentation paths.

## 3. Existing local health checks

Only if the services already run, these GETs check health without generating plans:

```sh
curl --max-time 5 http://127.0.0.1:8000/health
curl --max-time 5 http://localhost:3000/api/health
```

FastAPI should return `{"status":"ok"}`. The proxy returns status/backend metadata or 503 unavailable. Connection failure means no reachable service at that address; it does not establish a model or database defect. Health does not prove AI, Google or SQL readiness.

## 4. Offline checks with existing dependencies

Inspect [backend/TESTING.md](../../backend/TESTING.md) first. These commands execute project code and can create generated local files/temporary fixture processes. Normally enabled test transports are mocked; no running AI/Maps/hosted database is required. Do not enable private hosted/lifecycle flags.

```sh
npm test
npm run test:backend
npm run lint
npm run build
npm run typecheck
```

Run build to completion **before** typecheck because build replaces generated `.next/types`. Build is a frontend packaging check; backend hosted startup still refuses. Relevant focused examples:

```sh
backend/.venv/bin/python -m unittest backend.test_planner backend.test_ranking -v
backend/.venv/bin/python -m unittest backend.test_hitec_geography -v
```

Run tests only after reading what they replace and what resource flags are absent. The complete backend suite includes normally skipped hosted SQL and PTY lifecycle checks. A failed environment/socket permission is not a semantic pass. Report actual totals, errors and skips from your run; checked-in historical numbers are not today's results. This documentation delivery did not rerun application suites.

## 5. Normal startup — can load the owner's real profile

The root [README](../../README.md) is the startup authority. In separate Terminals, from the working folder:

```sh
npm run dev:backend
```

```sh
npm run dev
```

The owner launcher loads its approved ignored local profile and restricted saving configuration; fresh clones without that profile remain mock. Starting the backend may prepare local AI readiness; deliberate real planning/lookup/details can spend Google allowance. These are not required handbook verification commands. Explicit fictional mode uses:

```sh
npm run dev:backend -- --mock
```

Even mock outings still use local interpretation for fresh natural language. Do not describe mock startup as all external/model work disabled. Stop only your own foreground process with Control+C. Do not kill unknown listeners or stop owner services just to run optional lifecycle tests. Keep ordinary backend bound to loopback as configured.

## 6. Later isolated practice

See [exercise setup](LEARNING_EXERCISES.md) before creating a worktree/branch. `git worktree add` and dependency installation change local state. Do not copy private profiles into a scratch checkout. A prose patch proposal or fictional calculation is enough for the course's modification lessons.

## 7. Commit/push only the intended work

Before an authorized documentation delivery, inspect status/diff/new files, then stage explicit paths. For this handbook the intended set is `docs/learning/`, `README.md`, `HANDOVER.md`; V5 implementation/research files must remain unchanged. Do not mechanically run `git add .`. A push publishes commits to the configured private remote and requires the owner's authorization; this handbook task explicitly grants it, ordinary study does not require one.

## Commands deliberately excluded from exercises

Do not run cloud model live/readiness/counting/account scripts, AI smoke/evaluation scripts, database setup/migration/hosted checks, billing/quota commands or real Maps calls to verify prose. Do not clear journals/halts, delete cost ledgers, print all environment variables, open private credential files, reset/clean the working tree, force-push or start Task 53. None is necessary to learn the implementation.

## Disposable V5.1 application workflow

The exact loopback-only launch commands, server-owned examples and shutdown boundaries are in [the local integration report](../task52-v51-local-application-integration.md#local-use). Run `node --import tsx --test lib/v51-application.test.ts` for the automated application-boundary checks. This never selects V5.1 in normal startup.

## Deployment packaging checks (no deployment)

From the repository root: `npm run build`, then `backend/.venv/bin/python -m unittest deployment.test_packaging -v` runs native isolated payload checks. `sh deployment/container-smoke.sh` separately requires a running local Docker engine and builds Linux amd64 images. It makes no cloud deployment or provider request; missing Docker is a blocker, not a pass. See [environment contract](../../deployment/environment-contract.md).
