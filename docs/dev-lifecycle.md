# Local development shutdown and restart

November 2, 2026. Narrow development repair; Tasks 50/50A–50E remain unstarted.

## Evidence and cause

The initially occupied backend port belonged to the preceding Codex acceptance run:
its npm parent was still alive, Python ran this repository's `backend.dev_start`,
and the reload supervisor and multiprocessing server shared the same listening
socket. It was a healthy background instance, not an orphan. SIGINT to that npm
parent stopped both Python processes and released 8000. The original frontend was
also an identified live repository instance. No ordinary Control+C leak was
reproduced; the owner's precise interrupted-Terminal sequence remains unknown.

A controlled legacy reproduction did establish the orphan failure path: start the
old direct Python launcher in its own process group, SIGKILL only its reload
supervisor, and its child still serves `/health` and holds 8000. Uvicorn's installed
BaseReload.shutdown also calls an unbounded child join. Thus a lost supervisor or
hung child can prevent reliable cleanup; two listening PIDs alone do not prove a bug.
Plain Next dev also permits automatic alternate-port selection without explicit
`--port`. The first new preflight implementation's IPv6-only probe missed an IPv4-only
listener; regression tests now cover both address families.

## Supervision

Both npm development commands enter `scripts/dev-server.mjs`. Production build/start
and the backend application are unchanged. The existing Python launcher still loads
and validates the ignored owner profile, restricted database identity/TLS and mock
override; Uvicorn retains its native reload supervision. Next retains its native HMR
and uses explicit port3000. Proxy destination/port8000 remain unchanged.

A small IPC-connected guardian launches each runtime in its own process group on
POSIX. Control+C/SIGTERM/terminal SIGHUP initiates shutdown once. The runtime leader first receives
SIGTERM, allowing Uvicorn/Next to stop their workers and release sockets. The guardian
waits for the owned group to disappear and the fixed port to become bindable. A stuck
owned tree gets an eight-second grace period before bounded group termination, with
an eleven-second outer deadline. Repeated signals do not create competing cleanup.
Next's own child grace timeout is five seconds rather than its installed100ms default.
The npm command remains alive until the guardian finishes. IPC disconnection also
cleans the runtime when the outer launcher disappears; this is not a persistent daemon.
No automatic provider requests, retries, database writes or ledger resets are added.
Ollama's existing daemon-thread preparation and its local-only gates are unchanged.

## Ownership and conflicts

`backend/.local/dev-servers/` is ignored, owner-only0700, with0600 regular metadata
files. Symlinks/unsafe permissions are rejected. Records hold a random256-bit local
control credential, canonical repository path, service and an ephemeral loopback
control port. Credentials are never printed. Live token-authenticated responses must
match repository and service; process names or stale PID files are never kill authority.
The control endpoint binds loopback only; unauthenticated requests receive404.

A healthy existing launcher is left running; a second start explains reuse or Control+C.
An occupied unverified port is left untouched, with no alternate port or lock deletion.
Dead metadata can be replaced only during a free-port launch; it cannot authorize
process termination. Concurrent starts use exclusive metadata creation.

Exceptional `npm run dev:backend -- --stop` / `npm run dev -- --stop` requests authenticated
graceful shutdown, waits for release and refuses unverified legacy/unrelated listeners.
It is an explicit stop action, never an automatic side effect of starting twice.
Normal daily use needs only the two documented startup commands and Control+C.

## Verification

The opt-in local harness uses real pseudo-terminals, writes the terminal interrupt
character, checks actual process ancestry disappearance and binds the released port:

```bash
# First stop both development terminals. Unknown listeners are never killed by tests.
cd ~/Documents/whereto
WHERETO_LIFECYCLE_TESTS=1 backend/.venv/bin/python -m unittest backend.test_dev_lifecycle -v
```

Eight scenarios cover five backend and five frontend full start/Control+C cycles,
Uvicorn edit reload, direct/proxied health and frontend page200, healthy duplicate
refusal, abrupt outer-launcher loss, unrelated IPv4 listeners on both ports, owner
real-profile health, repeated interrupts, rapid mock restart and actual mock plan
creation, legacy orphan reproduction/controlled cleanup, stale metadata replacement,
authentication refusal/explicit stop, and a frozen supervisor's bounded cleanup.
All provider planning uses mock data; no billable Google requests occur. The one real
profile startup preserves existing local Ollama preparation, without calling Google.
Tests do not reset the owner ledger or use administrator database credentials.

This is actual controlled PTY Control+C testing on macOS, not automation of the owner's
Terminal windows. Linux/Windows lifecycle behavior has not been certified here. A
machine crash, SIGKILL of the guardian itself, or a legacy
unverified process can still require exceptional manual investigation. The launcher
never guesses identity and kills an arbitrary listener to hide such a conflict.

Final results: opt-in lifecycle **8/8** in36.388s; full backend **671 run; suite OK with28
reported skips** (20 hosted plus8 separately run opt-in cases); frontend **232/232**. TypeScript,
ESLint, production build and Python dependency consistency passed. No hosted database
writes were needed. Tests ended with both ports free and no private runtime metadata.
