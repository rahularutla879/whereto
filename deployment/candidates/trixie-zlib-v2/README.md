# Inactive Trixie zlib security delta

No runtime is selected, security exception accepted, service published or spending granted.
The original Bookworm and Trixie-v1 artifacts remain intact. Exact six local OCI IDs
are in `images.json`; these are not yet registry manifest digests.

The only OS package change is zlib1g to `1:1.3.dfsg+really1.3.1-1+deb13u1`.
`security-package.json` pins the official Debian security archive using the SHA256
verified against signed APT metadata. Obtain that exact archive separately; do not
commit it. From `/Users/rahularutla/Documents/whereto`:

```sh
TASK52_SECURITY_DEB=/tmp/reviewed-zlib1g.deb backend/.venv/bin/python -m unittest deployment.test_zlib_candidate deployment.test_candidate_promotion -v
backend/.venv/bin/python -m deployment.prepare_zlib_candidate /tmp/whereto-zlib-review /tmp/reviewed-zlib1g.deb
```

The target must be fresh and outside Git. Use the `roles` context and its derived
Dockerfile for each existing ROLE, and `frontend-trixie-next` with its derived
`deployment/Dockerfile.frontend-private` for frontend; always Linux amd64 and local
tags. Both dependency/build and runtime stages inherit the exact patched base.
BuildKit mounts the archive read-only during installation; it is not copied into
runtime layers. No broad APT upgrade, package purge or unpinned download.

Next 16.4.5 uses the unchanged candidate-only lock in `../trixie-v1/`.
`LOCAL_FIXTURE=false` is mandatory; the separately built browser-test frontend is
ineligible for promotion. No test signer or owner credentials enter these images.

`promotion-PROPOSED.json` gives two guarded, exact-byte shadow replacements under
`proposed/`. Nothing applies them automatically; both remain launchable=false.
Security disposition, explicit owner promotion and separate hosted enrollment are
still required. Follow its drain/fence/session invalidation/code-only rollback
rules; never roll back financial, session or independent witness history.

See `docs/task52-candidate-promotion.md` for same-database security comparison,
functional verification, known failures and remaining deployment gates.
