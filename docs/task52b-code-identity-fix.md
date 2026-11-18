# Task52B — offline supervised GET code-identity correction

Baseline `1d994c2dd8f2727d01e3df7ed1bd9ba2ef1c6404`. [Versioned build](task52b-model-get-build-v2.json), [verification and retained attempts](task52b-code-identity-fix-verification-v1.json).

**The reproducible local defect is fixed and the actual supervised path passes over local TLS. No real credential, provider request or live authorization was used.**

## Exact root cause and evidence

At the baseline, `scripts/task52b_model_get.py:108` in `verify_supervision` compared `runtime.loadedWireBytecodeSHA256` with `sha256(marshal.dumps(GetOnlyHTTPS.exchange.__code__))`. `execute_get_only` captured the earlier hash before entering the method. CPython3.12.1 marshal serializes reference-sharing state: the unchanged function's serialization can change when a local variable holds an additional reference to a string in its constants. After assigning the fixed path and other locals, the post-TLS check rejected unchanged code.

A controlled probe on the same code object held one reference to the path constant. Its measured reference count changed2→3; marshal SHA changed `e427db367dd903016b459a29061f2e10e6d967ab68daa5d24303f89321f770b1`→`6f11db7f45d52def45207c77df011172ef1d233cc63542531efdb323cb151999` and reverted after release. Source SHA `4591c22d08af3a76a2bf94edd2d77058d5c61f43bdca450260564251bada877f`, public bytecode SHA, class, interpreter and code object stayed unchanged. This was not an AST/source hash, import, class-ID or interpreter-version mismatch.

Before changing production code, the new actual supervisor/worker/credential-loader/TLS test failed: `get_worker_identity` at line108, wire claim present, no HTTP result. Test-only allowlisted exception tracing captured the branch. No application validator, credential loader, writer, supervisor or exchange was replaced. After correction the same test succeeds. A final negative control loads the original Git-pinned defective source into the same isolated harness and still reproduces that refusal. The historical live capture remains only `Refused`; its exact original branch is not retroactively certified.

## Correction without removing identity checks

`scripts/task52b_code_identity.py` defines versioned deterministic identity from typed public code fields: bytecode, recursively typed constants/nested code, arguments/locals/flags, names, variable/free/cell names, filename/qualified name/line and exception tables. Defaults and keyword defaults are included. It omits mutable reference counts, intern/reference-sharing flags and adaptive interpreter caches, not semantic constants. Unsupported types/defaults fail closed; no pickle/marshal or executable deserialization is used.

Expected identities are independently compiled from SHA-pinned source without executing it, then pinned in the new build. Loaded functions must match those expectations, qualified names, defaults and original module-global namespace/closure bindings. Fourteen selected callables include the exchange, dial/TLS initializer, writer/fsync, reader/metadata, request/intent/supervision/worker/runner/preconditions. Class/base/initializer/constructor/attribute-access bindings are checked. This strengthens the old self-derived runtime hash, which could otherwise bless a substituted method before capture.

Runtime facts now require `identityScheme=52b-source-compiled-code-v1` and `loadedWireIdentitySHA256`; old marshal facts are not migrated or reinterpreted. Source, normalized bootstrap, interpreter and CA pins remain. Existing TLS, credential/project/stat checks, INTENT-before-key-load, exclusive claims, no retries, response bounds and terminal failures remain intact. Normal application/startup/financial SQL are unchanged. Trusted interpreter/stdlib and operator filesystem/bootstrap remain trust assumptions; this is not a sandbox against an administrator able to replace the whole checker.

## Integrated regression scope

The fixture uses a temporary source/config/evidence root, fictional key and prior records, actual private-file checks, independently spawned parent/child via `python -I -B`, and a controlled TLS server. Only fixture configuration constants, local DNS routing and the trusted fixture CA are supplied. Socket connections are restricted to the exact loopback port, environment contains only PATH/LANG/TMPDIR, and no owner dotenv/private evidence is copied. An audit hook proves durable consumption/INTENT exists before the fictional key is opened. The real exchange/identity checks execute. Fixture support is excluded from images by the existing `backend/*fixture*.py` rule.

Coverage includes repeated fresh interpreters; original-code negative control; changed source, constants, method/dial/class/constructor; wrong build/bootstrap/metadata; absent/expired fictional authorization;401/403/malformed/wrong-model terminal responses; process death before/after INTENT and after send; competing supervisors; replay; CLI purpose and parent/worker guards. Five misleading mocked GET-supervisor tests were replaced by seven integrated tests; pure CLI/PID checks remain and protocol/TLS tests remain. No frozen evaluator tests were removed or repinned.

## Exact verification and limits

Final **110current-source tests passed (77.705s),15frozen-compatible tests passed (1.368s),0failures/errors/skips**. Original test failed before correction (1failure), first fixed run6passed, extended run12passed, earlier full run110passed. All logs/source snapshots are retained by hash. One inventory command had an unmatched zsh glob; `rg --files` corrected the inspection without changing files. Dependency consistency, diff, source and secret-pattern checks passed; no dependency changed. Full backend/B2/SQL/Redis, frontend/build/browser/container suites were not run or claimed.

Original paid history10/$0.047366625/$11.952633375 remaining/324files/five payload pairs/halt is unchanged. Original13-file pair, failed10-file GET scope and its actual authorization hashes are unchanged. `52b-model-get-owner-128fa8c-v1` remains unusable; old authorization's build refuses under the new source. Original GET expiry stays November18,00:00UTC. No actual credential values were read, no live authorization was created/consumed and no real provider operation occurred. Chapters14/15 reviewed unchanged;17 updated;20chapters preserved.

**A NEW GET-only scope can now be prepared for separate owner approval.** This checkpoint does not prepare/enroll that live scope, send a GET, certify model availability or enable counting/inference. The separately pinned count runner still contains its own old marshal check; it was deliberately not modified and needs its own compatible migration/testing before any live count authorization. No infrastructure/deployment/Task53 work begins automatically.
