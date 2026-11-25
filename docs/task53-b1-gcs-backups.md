# B1 GCS destination — owner decision, no execution authority

GCS replaces the uncreated iCloud folder. Existing B1 export, encryption, exact comparisons and source deadlines remain unchanged. [Machine-readable proposal](../deployment/cloud-run/b1-gcs-destination-PROPOSED-v1.json). No resource, IAM, software installation, genuine key, live export or upload is authorized.

## G1: smallest next decision — one empty bucket

Proposed name `gs://where-to-512422-b1-backups-us-east4`, project `where-to-512422`, regional Standard. Public access prevention enforced; uniform bucket-level access. Seven-day **unlocked** retention and seven-day soft delete; versioning off with unique create-only object names. No Autoclass, automatic lifecycle deletion, website, public link, CMEK or application credentials. Retention lock is irreversible and is not proposed. An administrator can change unlocked policy: this does not establish independent custody. [Retention](https://docs.cloud.google.com/storage/docs/using-bucket-lock), [soft delete](https://docs.cloud.google.com/storage/docs/soft-delete).

After explicit approval, fresh project/API/bucket-name/IAM/billing checks must pass. Create at most once, stop on errors/unexpected bindings or charges, then independently describe raw metadata and IAM. Do not enable APIs or silently remove default/inherited bindings.

```sh
cd /Users/rahularutla/Documents/whereto
/opt/homebrew/bin/gcloud storage buckets create \
  gs://where-to-512422-b1-backups-us-east4 \
  --project=where-to-512422 --location=us-east4 \
  --default-storage-class=STANDARD --uniform-bucket-level-access \
  --public-access-prevention --soft-delete-duration=7d \
  --retention-period=7d --no-enable-autoclass --quiet
```

**Proposed approval wording:** “Authorize G1 only: create this one empty private Standard bucket with the exact settings above, maximum $1 one-time and $1/month gross, subject to verified account charges. No IAM enrollment, objects, API enablement, keys, live database access or provider operations. Stop if the envelope cannot be respected.” This proposal is **not approved**, and Google provides no bucket byte/billing hard cap. No further owner signature is invented or required by this preparation.

## G2: scoped identities — separately approved later

None of the six runtime identities is appropriate for manual backup writing. Propose one dedicated `whereto-backup-writer` service account, create-only on this bucket. No service-account keys. A named writer operator may mint access tokens for that account only, using a custom `iam.serviceAccounts.getAccessToken` role; no signBlob/signJwt authority.

Recovery/deletion administrators are **not selected**. Per owner direction, leave both unassigned; this does not block preparing G1. Later choose three distinct named users:

| Principal | Exact scoped authority |
| --- | --- |
| Writer operator | Access-token minting on backup writer only |
| Backup writer SA | Bucket `roles/storage.objectCreator`; cannot read/delete/overwrite |
| Recovery reader | Bucket custom `storage.buckets.get`, `storage.objects.get`, `storage.objects.list` |
| Deletion operator | Bucket custom `storage.objects.delete`; cannot read/write or change IAM |

`deployment.b1_gcs.iam_commands()` refuses missing/public/runtime principals and produces eight commands only when all three names exist: one SA, three custom role definitions, four exact bindings. It neither executes nor grants project-wide roles. Re-review inherited project administration and actual custom-role support before G2. Unexpected convenience/default IAM bindings stop enrollment. No bucket-IAM administration is delegated. [Official permissions](https://docs.cloud.google.com/storage/docs/access-control/iam-roles).

Soft-deleted-object restoration requires **create plus restore** permissions; it is deliberately outside initial read-only recovery authority. That exceptional operation needs separate approval, sufficient headroom and version/hash verification. Retention may prevent deletion even by the delete-only principal. No automatic deletion of the last verified recovery point.

## Cost and bounded usage

Official regional `us-east4` prices observed November25,2026, USD, no credits/discounts assumed. The public table defaults to another region; the proposal records the us-east4 selector values and fetched page hash. [Pricing](https://cloud.google.com/storage/pricing).

| Class | GiB/month | Minimum duration | Retrieval/GiB | Class A / B per1,000 |
| --- | ---: | --- | ---: | --- |
| Standard | $0.023 | None | $0 | $0.005 / $0.0004 |
| Nearline | $0.013 | 30days | $0.01 | $0.01 / $0.001 |
| Coldline | $0.006 | 90days | $0.02 | $0.02 / $0.01 |
| Archive | $0.0025 | 365days | $0.05 | $0.05 / $0.05 |

Recommend Standard for short rolling backups and repeated recovery checks: no minimum-duration/early-deletion fee or retrieval charge. Colder classes can cost less for genuinely long-held copies; this is not a claim Standard is always cheapest. Upload ingress is free; operations are charged. Ordinary US internet recovery egress is $0.12/GiB. Live, noncurrent and soft-deleted bytes all bill. No versioning duplication is proposed.

300MiB costs ~$0.00674/month storage;600MiB including deleted/restored copies ~$0.01348/month. Low-use estimate (600MiB,0.25GiB download,100A/100B) ~$0.05/month before tax. Conservative31-day scenario (600MiB,1GiB download,1,000A/1,000B) **$0.139136 before tax**. Account currency/tax, applicable discounts and actual invoices remain unverified; proposed gross $1/$1 ceilings are unapproved. No fixed compute/KMS charge or subscription is proposed; even an empty bucket can incur control-plane operations.

Limits:64MiB **combined** per complete four-object generation;300MiB live,600MiB total billable; latest three verified plus one pre-change generation; at most eight new generations/month. Fresh recovery-reader inventory must include soft-deleted versions/restored duplicates. Refuse if full; do not enlarge limits or delete protected copies automatically. These are client admission limits, not cloud-enforced quotas; a compromised writer/project administrator can exceed them. Monitoring/account oversight remains necessary.

## Exact recovery sequence and custody

1. Separately authorize the original B1 operator/export scope: at most three source sessions, **60seconds shared**, direct IPv6/verify-full TLS,2s connect,250ms initial dump-lock wait. Application1500/250ms deadlines unchanged. No B0 repeat.
2. Reuse `b1_pipeline` for encrypted baseline-before, custom dump and baseline-after. Encrypt the bounded verification receipt too. Only `before.json.cms`, `application.dump.cms`, `after.json.cms`, `receipt.json.cms` enter GCS; no plaintext, passwords, recipient private key or dashboard secrets.
3. Validate successful B1 receipts and CMS AuthEnvelopedData structure; local structure checks cannot certify producer identity. Pin recipient/tool/source identities and hash the completed ciphertext. Fresh capacity/IAM checks precede upload. Create exact generation names with `--if-generation-match=0`; no overwrite or automatic retry/resume.
4. The separate recovery reader obtains actual server metadata and independently downloads **each exact server generation**, using a fresh0700directory and new0600files. GCS metadata supplies generation/CRC32C/MD5, not trusted SHA256: compute downloaded SHA256 against the independently retained B1 receipt. Record actual object generation and hashes; do not treat a simulated upload as cloud proof.
5. Owner-authorized decryption must authenticate AES256-GCM completely **before** pg_restore; never pipe unauthenticated plaintext straight into restore. Fresh isolated PG17, six tables, data/counts/schema/owners/grants/forced-RLS/dependencies/source-before-after must match. Enroll a recovery point only after all comparisons pass.
6. Custodian retains separately protected encrypted private-key/passphrase recovery access, trusted hash receipt and at least one verified ciphertext copy **outside this GCP project**, e.g independently held offline media. Same-project GCS cannot defeat compromised project administration. No second cloud purchase is assumed. This does not replace independent financial-witness administration or authorize operational/witness rollback.

Supported SDK590 transfer overrides are per-process only: `CLOUDSDK_STORAGE_MAX_RETRIES=0`, `CLOUDSDK_STORAGE_PROCESS_COUNT=1`, `CLOUDSDK_STORAGE_THREAD_COUNT=1`, `CLOUDSDK_STORAGE_PARALLEL_COMPOSITE_UPLOAD_ENABLED=False`, `CLOUDSDK_STORAGE_SLICED_OBJECT_DOWNLOAD_THRESHOLD=0`, `CLOUDSDK_STORAGE_RESUMABLE_THRESHOLD=67108865`. SDK default retries23 are not acceptable for this bounded proposal. No global config changes, signed URLs, static credentials or environment-secret sourcing. A later source-bound operator enrollment must supervise/record the exact generated commands; this helper is not a live backup runner.

Coverage remains application-only: six whereto tables, schema/data/indexes/constraints/triggers/RLS/grants and reviewed dependencies. `public.rls_auto_enable` remains excluded subject to dependency refusal; no implicit extension install. Managed Auth/Storage/Vault, Storage bytes, dashboard settings, unrelated keys and full Supabase administrator recovery are excluded. See [original B1 commands](task53-b1-application-backup.md).

## Tools and owner key — separate approval, no genuine material accessed

Keep the [exact manual RSA3072 encrypted-key commands](task53-b1-owner-prerequisites.md#owner-only-manual-key-creation--only-after-approval), unchanged. Run them yourself only after approving creation, from `/Users/rahularutla/Documents/whereto`; never reuse frontend Ed25519. Only public certificate/SPKI fingerprints may be shared. Private key/passphrase stay outside Git/images/GCS/deployment secrets. Genuine custodian enrollment remains pending.

Prefer the isolated official [Postgres.app2.9.7 PG17.12 Universal asset](https://github.com/PostgresApp/PostgresApp/releases/download/v2.9.7/Postgres-2.9.7-17.dmg), **119,766,608bytes**, published SHA256 `e1f45cf63f2dfc4120e9ef3caae7ffe70dade56d54b9f0e00235dce347f847c9`. [Official release metadata](https://api.github.com/repos/PostgresApp/PostgresApp/releases/tags/v2.9.7).

First request download-only approval, at most120MiB; no installation. After download compare byte count/hash, run signature/Gatekeeper verification and independently confirm the Developer ID against the official publisher; stop on mismatch or unknown identity. Actual signing identity, notarization and native compatibility cannot be verified from the release hash alone and are **pending**. Only then separately approve isolated bundle installation and pin `Contents/Versions/17/bin/{psql,pg_dump,pg_restore,initdb,pg_ctl}` versions/hashes/native dependencies. Do not open GUI, initialize persistent cluster, start a service, edit PATH/Homebrew/SDK or remove quarantine. Cached PG17.11 network-none fixtures are only offline alternatives; their VM has no IPv6 default route and is not a proven live-export client.
