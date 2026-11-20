> November20update: owner trust selection and frontend-only local rebuild/scan are now verified. [New inactive image and exact remaining approval](task52-owner-frontend-rebuild.md). Do not regenerate the owner's key/challenge/signature or repeat this build. The preparation narrative below preserves the original workflow; no publication/configuration/hosting approval has been issued.

# Private production enrollment — prepared, not authorized

Six image/config identities remain exactly [real-native-v1/images.json](../deployment/candidates/real-native-v1/images.json). Actual local inspection reconfirmed all six IDs and default startup exit78 without network/secrets. No image changed; no redundant rebuild/scan is claimed. Original same-database counts remain0critical/77high per Python role and0critical/70high frontend. [23-advisory decisions](task52-production-enrollment-security.md) · [verification](task52-owner-enrollment-verification.json).

## Owner-controlled trust

`deployment/frontend_trust.mjs` reuses raw Ed25519/SPKI and the existing frontend signature format. It **contains no key generation, private-key parser or signing operation and accepts no owner-private-key argument**. Public-key/owner-signature records use owner-only0600files/0700directories, no-follow, exclusive creation and fsync outside the checkout. Proof establishes possession, **not independently certified human identity, risk acceptance or deployment authority**. Owner fingerprint confirmation is required.

The owner enrollment private key stays offline/encrypted, outside Git, images and build outputs. Never reuse the evaluation API key, witness key or runtime frontend forwarding key. Runtime forwarding material is separate and remains in the existing sealed Secret Manager contract.

From `/Users/rahularutla/Documents/whereto`, the **owner**, not Codex, may perform this workflow on a trusted workstation. Use an existing appropriate owner Ed25519 key when available; otherwise these are manual generation commands. Local nonsecret inspection found OpenSSL3.5.9 available at /opt/homebrew/bin/openssl; no key was read/generated. Stop if trusted OpenSSL3/Ed25519 is unavailable on the operator workstation:

```sh
openssl version
umask 077
TASK52_TRUST="$HOME/.whereto-production-frontend-v1"
mkdir -m 700 "$TASK52_TRUST"
mkdir -m 700 "$TASK52_TRUST/state"
openssl genpkey -algorithm ED25519 -aes-256-cbc -out "$TASK52_TRUST/owner.pem"
openssl pkey -in "$TASK52_TRUST/owner.pem" -pubout -out "$TASK52_TRUST/public.pem"
node deployment/frontend_trust.mjs request "$TASK52_TRUST/public.pem" "$TASK52_TRUST/state"
# Read selection.json. Verify source/cohort, public fingerprint and trust-only purpose.
# Sign ONLY after independently deciding to select this key.
openssl pkeyutl -sign -rawin -inkey "$TASK52_TRUST/owner.pem" -in "$TASK52_TRUST/state/selection.bytes" -out "$TASK52_TRUST/state/selection.sig"
node deployment/frontend_trust.mjs accept "$TASK52_TRUST/state" FINGERPRINT_SHOWN_BY_REQUEST
node deployment/frontend_trust.mjs rebuild-plan "$TASK52_TRUST/state" /tmp/whereto-owner-front-build /path/to/reviewed/zlib1g.deb
```

Passphrases go only into OpenSSL's non-echoing terminal prompt. Never paste secret material into chat, shell arguments or logs. Use a fresh versioned directory; stop on existing paths rather than overwriting evidence.

The final command prints existing source-pinned prepare/check/frontend-build argv; it executes none. Run prepare, then `check-context` before building. Every approved context byte is verified; altered/missing/extra files, symlinks, wrong Dockerfile/dependencies/cohort refuse. Only the public key becomes a build argument. Five Python images stay unchanged.

After the owner-authorized local frontend rebuild, scan the new exact image with the existing scanner, preserving all old candidates. Then:

```sh
node deployment/frontend_trust.mjs record-frontend "$TASK52_TRUST/state" sha256:ACTUAL_NEW_FRONTEND_ID /path/to/new-frontend-grype.json
```

This verifies actual image/non-root/closed startup, bootstrap/application hashes, unchanged approved source inputs/outputs, owner public key, frontend pin, and scan-to-actual-OCI-config binding. It writes only an **unsigned proposed** replacement record after verification. No genuine record/replacement was generated in this checkpoint: the owner key is absent.

For configuration, `configuration-request TRUST_DIR ACTUAL_FRONTEND_BUILD_JSON OWNER_ONLY_CONFIG_JSON FRESH_OWNER_ONLY_OUTPUT_DIR` emits only the exact artifact/configuration-hash/purpose challenge. Owner reviews both protected configuration and proposal, signs `enrollment.bytes` into `enrollment.sig`, then runs `configuration-finalize TRUST_DIR OUTPUT_DIR`. Its result passes the existing production `realConfiguration` format. Public traffic and financial authorization remain false. No owner signature is manufactured.

## Exact publication batch

After the real frontend record and an actual artifact/security decision exist:

```sh
node deployment/frontend_trust.mjs publication-request "$TASK52_TRUST/state" SHA256_OF_ACTUAL_SECURITY_DECISION
# Owner reviews publication.json: exact six IDs/configs, source, security reference and costs.
openssl pkeyutl -sign -rawin -inkey "$TASK52_TRUST/owner.pem" -in "$TASK52_TRUST/state/publication.bytes" -out "$TASK52_TRUST/state/publication.sig"
python3.12 -m deployment.publication_batch "$TASK52_TRUST/state" /path/outside/git/approved-publication.sh
```

**Do not run the batch without separate explicit publication approval.** It verifies the owner-supplied signature/source binding before Docker, consumes one authenticated in-memory snapshot, checks six local Linux amd64 images/aggregate uncompressed size≤5GiB and contains exactly six fixed-repository tag/push pairs. Tags include immutable image IDs. No gcloud, Run, IAM, secret, provider or financial-grant command follows. Stop on first error; no automatic rerun. This does not sandbox a compromised same-user operator/Docker daemon.

Capture actual future registry leaf-manifest/config bytes. Local image/index IDs, OCI config digests and registry manifests remain distinct. The owner-bound compiler reuses the existing exact compiler with the signed frontend replacement without overwriting old cohorts/pins:

```sh
python3.12 -m deployment.publication_batch "$TASK52_TRUST/state" /path/outside/git/cloud-plan.json --cloud-plan /path/to/nonsecret-staging-inputs.json --registry-receipts /path/to/actual-registry-receipts
```

No genuine proof means refusal; missing registry bytes means no deploy argv. Output is review-only. Artifact approval cannot accept hosting risk, qualify a model or grant spending.

## Proposed first purchase decision — NOT approved

One private immutable-tag Docker Artifact Registry repository `whereto-private`, project `where-to-512422`, region `us-east4`, six exact owner-signed images,5GiB maximum. Publisher access is repository-scoped; no service-account JSON key.

[Public registry pricing](https://cloud.google.com/artifact-registry/pricing): approximately$0.10/GiB-month, so5GiB≤$0.50/month gross, without assuming the shared free allowance. Upload/same-region Google transfer is free under published terms. [Standard scanning](https://cloud.google.com/artifact-analysis/pricing):$0.26/image, six initial scans$1.56 if explicitly approved/enabled; account/Security Command Center terms may differ. **Proposed cap:$5 one-time setup/scanning,$1/month recurring registry storage.** This is not a provider-enforced billing cap.

Before creation/push, separately authorize read-only account/billing/API/scanning/repository observations. Stop if currency/tax, trial/permissions, actual scanning categories or fees exceed the cap. No billing upgrade, scanning enablement or purchase is implicit.

Exact proposed owner wording: “I approve the artifact-only batch in where-to-512422/us-east4: one private immutable-tag repository whereto-private, the six exact owner-signed images,5GiB,$5 one-time/$1 monthly ceilings subject to verified account charges. No Cloud Run services, public access, provider calls, financial grants or subscription/billing upgrade.” Fill actual frontend/security evidence first; Codex has not made this decision.

## Required inputs before private hosting

| Input | Current fact / next specific action |
|---|---|
| Frontend | Owner selects/signs public trust as above; actual frontend build/scan/record follows. No fixture signer may be represented as genuine. |
| Security |2missing Perl components,17conditional application paths,4unresolved native judgments. Obtain the missing bounded native-callsite/risk decision and confirm host conditions. No reviewer needs to rediscover measured facts. No risk accepted here. |
| Redis | [Official regions](https://redis.io/docs/latest/operate/rc/supported-regions/) confirm Essentials on GCPus-east4. [Starting price](https://redis.io/pricing/) is$5/month/$0.007hour, **not an exact regional250MB RAM quote**. Obtain a non-purchasing quote for RAM-only250MB,TLS, distinct ACL publisher/reader,Lua/CAS,absolute expiry,noeviction,128MiB application bound,NAT allowlist, actual ACL/command limits,backup/egress terms. Essentials is public TLS, not Pro private networking. No Memorystore substitution. |
| Operational SQL | Supply actual project/plan/direct host/restricted roles/CA/headroom privately. [Published compute](https://supabase.com/docs/guides/platform/compute-and-disk): Micro1GB/shared60connections≈$10compute/month; Small2GB/shared90≈$15. Neither is qualified capacity. Reserve≥18connections plus platform use; benchmark unchanged1500ms statements/250ms locks. Prior local57014 throttling is not proof of Supabase capacity or fixed by a blind upgrade. |
| Connectivity | [Direct Supabase](https://supabase.com/docs/guides/database/connecting-to-postgres) is IPv6 or paid IPv4; [IPv4](https://supabase.com/docs/guides/platform/manage-your-usage/ipv4) is$0.0055/hour. Existing contract requires verified direct/session-affine5432 and exact roles; no transaction-pooler shortcut. Confirm actual network/plan terms. |
| Witness | Name an independent administrator and backup/restore owner; separate DB/credentials/epoch,≥22reserved connections. Two passwords under one restore owner do not qualify. Obtain actual plan/backup quote. |
| AI | Qualified application model/revision/project, applicable processing terms, current full-input/output/extra-fee policy and separate application credential. Task52B human review remains deferred; no readiness/inference authorized. Evaluation key and historical5704count cannot substitute. |
| Maps | Dispatcher workload OAuth/API/quota enrollment, exact current SKU rates/unit/geography limits, content/attribution decision. Provider content remains request-local; no snapshots or automatic paid refill. |
| Financial | Explicit global/day/session/outing/provider budgets, prices/expiry/account/model and independent SQL/witness grants. None installed. |
| Cloud | Six dedicated SAs with actual immutable subjects, private invoker roles/count-only counter→dispatcher, named IAP testers, role-owned Secret Manager versions/CA bundles. No shared admin, Owner/Editor, Mac ADC or host dependency. |
| Costs | Actual Redis/DB/backup/network quotes/account terms and explicit infrastructure/provider ceilings. Artifact-only$5/$1 and historical budgets authorize neither full hosting nor AI/Maps. Exact full monthly total remains unknown. |

[Google documents predictable service URLs](https://docs.cloud.google.com/run/docs/triggering/https-request): `https://SERVICE_NAME-PROJECT_NUMBER.REGION.run.app` for sufficiently short names. `proposed_service_urls()` calculates all six from the existing project number895186533714 and labels them `observed:false`. No dummy/synthetic service is needed just to predict URLs. Confirm project/SA subjects before enrollment and actual `status.url` before tester/provider actions; stop on mismatch. No URL was contacted or resource existence asserted.

## Finite execution order after separate approvals

1. Actual owner trust/security/artifact decisions → frontend-only rebuild → new-image scan/record → exact signed artifact/cost scope → approved private registry publication → real OCI receipts.
2. Approved operational SQL, independent witness, compatible Redis/private network resources. Only reviewed authority schemas/roles/migrations, separately authorized; preserve saved-plan RLS and all financial history.
3. Prepare six-service deployment: dedicated IAM identities, confirmed deterministic URLs and sealed source/epoch/storage configuration drafts, exact registry digests, private/no testers. This is not a claim that incomplete services can become healthy.
4. Separately approved genuine provider enrollment: qualified model, application credentials/OAuth, current counting/pricing/content rules and finite SQL/witness grants. These are prerequisites to successful startup under the existing closed contract. Complete deployment counter/recovery → factory/dispatcher → backend/frontend only after them; verify non-billable readiness and actual IAM/IAP/revision ownership. Deterministic URLs avoid a dummy/fail-start bootstrap just for discovery. Health never authorizes inference.
5. One separately approved real ordinary outing with exact token/unit/cost scope: interpretation, deterministic clarification, confirmed origin, bounded real Searches/Matrix, three ordered cards/View Plan. No retries or automatic next outing.
6. Desktop/mobile, owner isolation, discard/refresh without spend, hosted capacity/callback overlap/recovery and Mac-off acceptance. Additional real outings require inclusion in the explicit allowance. No public launch or automatic next roadmap feature.

**Stop:** owner key/actual approvals missing. No replacement image identity, publication, resource provisioning, real provider/key/account access or financial grant occurred. Prepared code cannot replace those external facts.
