# Container environment and secret contract

These artifacts do not enable cloud activation. `backend.admission.validate_environment` still refuses production and hosted markers including `K_SERVICE`; there is no ready/force flag. The backend image defaults to this refusal. Local smoke runs explicitly select the existing `WHERETO_ENV=test`, mock mode and a loopback synthetic unavailable AI endpoint, with no cloud marker or credentials. That setting does not bypass hosted refusal.

| Setting | Owner / contract |
|---|---|
| `PORT` | Runtime integer 1–65535, default 8080; bind 0.0.0.0. Frontend and backend are separate Cloud Run ingress containers. |
| `BACKEND_URL` | Frontend server only, explicit HTTPS origin without credentials/query/path. Plain HTTP permitted only for loopback native/shared-network-namespace smoke. Current proxies have no Cloud Run IAM identity-token adapter; private backend invocation is blocked pending implementation. Never a `NEXT_PUBLIC_` value. |
| `WHERETO_ENV` | Backend defaults production. Existing guard refuses; no override can unlock a hosted environment. |
| `VENUE_DATA_MODE` | Packaging accepts mock only; real Places/Routes activation is unimplemented and unapproved. No mock result establishes live functionality. |
| `AI_PROVIDER`, `AI_MODEL` | Existing Ollama / qwen3:4b only. No replacement, bundled model weights or fallback. |
| `AI_BASE_URL` | Existing loopback HTTP Ollama dependency; cloud launcher permits only loopback and never discovers the Mac. Native smoke uses a fake HTTP 503 service, not Qwen. |
| `WHERETO_*_DEV` | Enabled development integrations rejected by launchers; no V5.1, diagnostics, warmup, real Maps or fixture switch. |
| `WHERETO_DB_HOST/PORT/NAME/USER/PASSWORD/SSLROOTCERT` | Backend only. Existing session-pooler port 5432, verified CA, `verify-full`, restricted `whereto_plan_runtime.<reference>` login. Never administrator login, service-role key, browser variables or baked secret file. Missing values refuse persistence, not a fabricated save. |

A future approved manifest must inject the password from a pinned Secret Manager version and mount a reviewed public pooler CA read-only at the supplied `WHERETO_DB_SSLROOTCERT` path. Supply non-secret host/name/restricted-role identity privately after owner confirmation. Backend identity needs only access to those exact secret versions and approved services; frontend identity must not receive database/model/Google credentials. Do not grant frontend broad cloud roles. Workload identity and private authenticated networking remain implementation blockers, not enabled by this document.

The `.env.persistence` fallback and local ADC file are absent from images. The runtime must not mount the owner's home, `.config/gcloud`, `.ssh`, repository, paid journal or evaluation evidence. Current Google transport still uses the local impersonation flow; an approved workload-identity adapter is required before real staging. No credentials are added here.

Uvicorn uses one worker, access logging disabled, and a five-second graceful shutdown. Native application logging keeps existing fixed codes/counts and omits bodies/tokens/locations. The Node launcher imports the generated standalone server in the same process so SIGTERM reaches it. Cloud Run startup/liveness overrides Docker health checks; process health is not dependency readiness. `/api/health` checks backend reachability, while backend `/health` does not prove AI/SQL/Redis availability. Do not send paid inference as a readiness check.
