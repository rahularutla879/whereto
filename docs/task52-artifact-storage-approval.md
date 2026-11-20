> Current repository update: owner separately authorized creation only. `whereto-private` now exists privately in `where-to-512422/us-east4`, Docker/standard, immutable tags, scanning explicitly disabled, zero images. Google added its documented first-repository service-agent role automatically; no public grant. [Verified outcome](../deployment/cloud-run/artifact-repository-enrollment-v1.json). **Do not rerun API enablement or repository creation. Uploads and runtime acceptance remain unauthorized.**

> Current update: Artifact Registry API alone is now enabled under separate explicit owner authorization. A propagation-aware read-only listing confirms zero repositories in us-east4; project IAM is unchanged and scanning APIs remain disabled. [Exact outcome](../deployment/cloud-run/artifact-api-enrollment-v1.json). Do not rerun API enablement. No creation, publication, cost or runtime-risk approval is implied.

# Exact private artifact proposal — unsigned, no execution

[Owner decision proposal](../deployment/cloud-run/artifact-storage-decision-PROPOSED-v1.json) · [complete byte-identical unsigned publication challenge](../deployment/cloud-run/artifact-publication-PROPOSED-v1.json) · [verification](task52-artifact-storage-verification.json). No private key or signature is committed. The owner-only challenge files were exclusively created/fsynced by the existing public-key workflow; no signature or approval was manufactured.

**Purpose:** private storage/review of these vulnerability-bearing images only. No runtime acceptance, configuration approval, application credentials, Cloud Run, testers, provider sends, financial grants or billing change. The five Python images retain their original Nov19reports(0critical/77high each); frontend Nov20report is0/72. Mixed database dates are explicit; no finding was suppressed or rescanned away. Conditional host/native/PBDS concerns remain hosting gates. Private artifact ACLs and inherited project access must be checked before upload.

| Role | Local image/index ID | Actual OCI config digest |
|---|---|---|
| frontend | `sha256:e4dd1587e926a51bc8ac0bcc2cefc2a85294fe8d196eced66868c4865bea7ccc` | `sha256:85dd5c1166163aacf666f12af1822a3168051fba0e59bac73cbe86992193171f` |
| backend | `sha256:a77800a1c78d1a15f749954b20bfd302ff2f98f237da73167a29c73522eae738` | `sha256:efccff6e32873726406c13ba279f23140239d03ddaf82eccb1407f3e48e7fbb8` |
| factory | `sha256:b08e851e74d6f7eb12b0b692e44b006ca87fff0469f06a23d9f0c34999af37a3` | `sha256:6edd9249751b84945104d490b6ba85ecffa3961fe3c5630ba366f3d5492e37c6` |
| counter | `sha256:101cf0e92fb3523b43f8218e8b9977f090fcc20feeb1bc164c26d5396fd226ad` | `sha256:a0ceac38af3e2bb602f14297b1b436cbd8c115d2d80c368a8271a37fa89d7bbb` |
| dispatcher | `sha256:4468969bf84573f48c28f5387a1533fe6e69a62ee735c72cdbcaf97f7ca7bac6` | `sha256:9f1c9e577b7bafbc66b5404882ad756384b4389fe5b08c0b53525ff87c82f93a` |
| recovery | `sha256:730765b775f833dbaad6cd2361d8d43a8b852e05cff18a1fe3fb06979965d655` | `sha256:5de182dc95db188dd98dc9f5ca0254998216fa2814351c31d22fec84fa1ba9c0` |

Source cohort: `5da873d60f542f266c8f7c4b0091995ed9b78084ae628e6c8bf56245e9a95e0d`. Archive indexes, amd64 leaf/config hashes, compressed layer digests AND uncompressed diff-ids verify; aggregate uncompressed bytes1,373,815,296(~1.28GiB), conservatively below5GiB even counting shared layers repeatedly. None of these IDs is asserted to be a future Artifact Registry manifest digest. Capture actual remote receipts after separately approved publication. No VM started/rebuild/rescan required.

**Decision SHA256:** `d18813d160029e293c4cc6679be6834db0c4bd223b09d8d1cc5cf73cb9abafa5`

**Exact unsigned publication-bytes SHA256:** `09a3ccaa87e702debc0fd2308d3bbf6587bad9ea1951e115cf20acd9bc64ebfe`

## Account/cost boundary

Six owner-authorized read-only CLI checks now pass: project ACTIVE; billing linked/open/USD; active CLI account has an existing direct project Owner role; no public project IAM bindings observed. At that initial read, Artifact Registry and scanning/Run/IAP/Secret Manager/Compute were absent from the enabled list. The separately authorized API update above now confirms Artifact Registry enabled and the target repository absent; other checked APIs remain disabled. Actual posted charges/tax/discounts/trial terms remain unknown. [Sanitized current observation](../deployment/cloud-run/artifact-account-observation-v2.json). The owner subsequently approved creation-only limits of$5one-time/$1monthly. Expected empty-repository usage is$0; this is not a posted-invoice claim or upload authorization. The documented Google-managed service-agent role appeared on first repository creation; no explicit IAM grant was made.

Proposed limits: one private immutable-tag Docker repository `whereto-private`,project`where-to-512422`,region`us-east4`;six exact images/max5GiB;$5one-time/$1monthly ceilings. [Public storage pricing](https://cloud.google.com/artifact-registry/pricing) gives about$0.50gross/month at5GiB before account-specific terms; do not assume shared free tier. [Scanning pricing](https://cloud.google.com/artifact-analysis/pricing) has account-dependent charges; this proposed new repository explicitly disables automatic scanning and enables no scanning API. Existing policies are not changed. Local full security evidence stays attached. These limits are operator stop conditions, not a provider-enforced hard billing cap. Stop if actual charges/terms cannot fit them.

## Owner actions

1. Exact API enablement and read-only repository checks are completed: Artifact Registry alone enabled; target repository absent; no public project bindings; scanning APIs disabled. Creation alone was subsequently authorized and verified; do not repeat it. Publication remains unauthorized. Confirm applicable account terms before any separately approved upload; USD/open status does not establish all charges.
2. Review the full proposed decision and publication JSON. Do not sign until account/cost/private-access conditions are established and you decide to approve artifact-storage-only scope. An owner signature on the existing domain binds the exact decision hash and image/config/cost set; it is not a hosting vulnerability exception.
3. After that decision, personally sign only `~/.whereto-production-frontend-v1/state/publication.bytes` into `publication.sig` with the already selected encrypted key. Codex must not open/sign with it. **No signature command was executed or real executable batch generated here.**
4. After the valid owner signature, generate/review the existing six-push batch; require separate explicit owner execution authorization before creating/uploading anything.

## Exact future commands — review only, not an executable batch

The following exact API command was already separately authorized and completed. **Do not rerun it**; no Run/IAP/Compute/SecretManager/scanning API was enabled:

```sh
gcloud services enable artifactregistry.googleapis.com --project=where-to-512422 --quiet
```

This exact creation command was separately authorized and completed once. **Historical command — do not rerun:**

```sh
gcloud artifacts repositories create whereto-private --project=where-to-512422 --location=us-east4 --repository-format=docker --mode=standard-repository --immutable-tags --disable-vulnerability-scanning --quiet
```

No IAM mutation, service account, scanning API or runtime resource is created by that argv. Existing approved publisher/helper configuration is required; do not print/export tokens or silently change credentials.

Only after actual signed approval:

```sh
cd /Users/rahularutla/Documents/whereto
node deployment/frontend_trust.mjs verify-publication "$HOME/.whereto-production-frontend-v1/state"
backend/.venv/bin/python -m deployment.publication_batch "$HOME/.whereto-production-frontend-v1/state" /tmp/whereto-approved-artifact-publication-v1.sh
# Review the six exact tag/push pairs. DO NOT execute without separate explicit authorization.
```

The existing renderer verifies the signature once into an exact image snapshot, checks6amd64 images/5GiB and emits6fixed-repository tag/push pairs. It cannot create Run services, enable APIs, mutate IAM/secrets, admit testers or authorize provider spending. Shell syntax and source/configuration tests pass(11trust+27publication/source); renderer inspected only in memory with a fictional missing-owner path. No actual batch or send authority exists.

Between publication and a real private URL remain separate runtime-risk disposition, Redisregional quote/ACL/network enrollment, operationalSQLcapacity/direct access, independentwitness ownership, qualifiedmodel/applicationcredentials/count/rates/grants, Googlecontent/attribution, sixIAM/IAP identities/namedtesters and role-owned SecretManager versions. This artifact proposal authorizes none of them.
