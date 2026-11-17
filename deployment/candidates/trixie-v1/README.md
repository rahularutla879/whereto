# Task 52 isolated Trixie / Next security candidate

Nothing here selects a production runtime, enables a provider, or grants spending.
The original Dockerfiles, Bookworm manifests, application package lock, Python locks
and protected SQL remain unchanged. `promotionApproved` is false.

`base-images.json` pins official Debian13 Python3.12 and Node24 images for amd64.
`cohort.json` binds their isolated projected runtime to the original source cohort.
`images.json` lists the five Python roles and combined Trixie/Next frontend for
review, the two frontend controls, and a clearly ineligible test-only browser image.
All responsibilities and application code reuse the existing projectors.

`next-package.json` and `next-package-lock.json` are candidate-only. Only Next,
@next/env and the matching SWC artifacts move16.4.2→16.4.5. The root lock and
unrelated optional-WASM metadata are preserved; no force upgrade was used.

To reproduce the isolated contexts from `/Users/rahularutla/Documents/whereto`:

```sh
backend/.venv/bin/python -m unittest deployment.test_trixie_candidate -v
backend/.venv/bin/python -m deployment.prepare_trixie_candidate /tmp/whereto-trixie-review
```

Use the exact base references in `base-images.json` as the existing Dockerfile's
`PYTHON_IMAGE` / `NODE_IMAGE` build arguments, always `--platform linux/amd64`.
For each Python role, use `/tmp/whereto-trixie-review/roles` as context and `ROLE`
as before. Frontend contexts are `frontend-trixie` (unchanged Next),
`frontend-bookworm-next` (Next-only control, original Bookworm base), and
`frontend-trixie-next` (combined candidate). Use their existing
`deployment/Dockerfile.frontend-private`. Default `LOCAL_FIXTURE=false` is mandatory
for any deployment candidate. Never deploy the separate `LOCAL_FIXTURE=true` test
image or fixture bootstrap material.

Security and functional results, residual findings and unrun scopes are recorded
in the Task52 Trixie report. Compatibility success is not independent risk
acceptance, operational enrollment, cloud provisioning or promotion permission.
