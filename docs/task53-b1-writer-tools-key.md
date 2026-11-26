# B1: three owner actions, no live backup authority

G1 is permanently complete. Do not create/list/reverify the bucket again. The [writer-only proposal](../deployment/cloud-run/b1-G2-writer-tools-key-PROPOSED-v1.json) and `deployment/b1_gcs_writer.py` prepare only the missing writer enrollment; they cannot execute cloud commands or load secrets. Original G1 evidence and the original all-three-operator renderer remain unchanged.

## 1. Approve G2-W only — four mutation commands, not yet executed

Use the existing project-owner Google account recorded in owner-only G1 metadata as the **proposed writer operator**. Its exact principal is in the ignored0600 batch `backend/.local/53-B1-G2-writer-preparation-owner-8377015-20261126-v1/writer-only-PROPOSED.sh`; the committed proposal contains only its SHA256. No fresh account access was made and no permission is granted by that file.

| Command | Exact authority/resource |
| --- | --- |
| Create service account | `whereto-backup-writer@where-to-512422.iam.gserviceaccount.com` |
| Create custom role | `projects/where-to-512422/roles/wheretoBackupTokenMinter`, GA, only `iam.serviceAccounts.getAccessToken` |
| Add service-account binding | That exact role on the writer account, for the named owner operator only |
| Add bucket binding | `roles/storage.objectCreator` on `gs://where-to-512422-b1-backups-us-east4`, for the writer SA only |

No project-wide binding, service-account key, signing/delegation authority, read/list/delete/overwrite grant, application-SA access or recovery/deletion enrollment. Writer identity alone cannot read/recover a backup. Predefined objectCreator contains additional create-related permissions; local B1 allowlists do not turn IAM into a ciphertext-inspection or byte-quota service. Existing project-owner and managed-service-agent storage authority remains inherited; this proposal does not revoke it or establish independent custody.

Before later execution, separately approved G2-specific read-only identity/IAM conflict checks must confirm the SA/custom role are absent and the existing bucket policy has not drifted. Stop on conflicts; do not update an existing role/account silently. No G1 inventory/creation replay. Afterward independently verify the enabled SA/no user-managed keys/no project roles; exact custom role; only the operator binding on that SA; and exactly the existing four convenience bindings plus one objectCreator binding on the bucket. `b1_gcs_writer` validates these policies without fabricating custodians. Preserve all other IAM/API/resources. No tokens need be minted or provider credentials enrolled for this batch.

**Proposed authorization:** “Authorize G2-W only: the exact four source-pinned commands for the saved project-owner operator, one new writer SA, one token-only custom role and two scoped bindings. Recovery/deletion remain unassigned. Allow bounded read-only G2 conflict/result checks; stop on errors/unexpected state or required new charges, no automatic creation retry. No API enablement, keys, object transfer, G1 replay or application grants.” No additional fixed subscription is expected for IAM enrollment; actual operation charges remain subject to the existing $1 one-time/$1 monthly envelope. This is not a new spending approval or billing hard cap.

## 2. Approve PG17 download/inspection only

Exact existing candidate: official **Postgres.app2.9.7 PostgreSQL17.12 Universal**, asset `Postgres-2.9.7-17.dmg`:

- URL: <https://github.com/PostgresApp/PostgresApp/releases/download/v2.9.7/Postgres-2.9.7-17.dmg>
- Exact size: **119,766,608bytes** (maximum120MiB transfer).
- Published SHA256: **`e1f45cf63f2dfc4120e9ef3caae7ffe70dade56d54b9f0e00235dce347f847c9`**.
- Official [release metadata](https://api.github.com/repos/PostgresApp/PostgresApp/releases/tags/v2.9.7); these are previously reviewed values, not a new binary download.

**Proposed authorization:** “Authorize one HTTPS download of this exact asset, including GitHub's HTTPS release-asset redirect, to a fresh owner-only local path, at most120MiB, zero retries/substitutes. Authorize hash/size/image-integrity checks and one read-only no-browse/no-autoopen mount solely to inspect the contained app's Apple signature and Gatekeeper assessment. Detach only that mount afterward. No copy/install, application or PostgreSQL binary execution, GUI, service/cluster, Homebrew/SDK/PATH change, quarantine removal or trust exception.”

After separately authorized acquisition, run these checks against enrolled exact local paths, recording each exit/result:

```sh
/usr/bin/stat -f %z "$B1_DMG"
/usr/bin/shasum -a 256 "$B1_DMG"
/usr/bin/hdiutil verify "$B1_DMG"
# If separately approved as above: readonly/no-autoopen mount; select only its returned path.
/usr/bin/codesign --display --verbose=4 --requirements - "$B1_APP"
/usr/bin/codesign --verify --deep --strict --verbose=4 "$B1_APP"
/usr/sbin/spctl --assess --type execute --verbose=4 "$B1_APP"
/usr/sbin/spctl --assess --type open --context context:primary-signature --verbose=4 "$B1_DMG"
```

The app and container assessments are separate. The [publisher's discussion](https://github.com/PostgresApp/PostgresApp/issues/792) describes historical differences; it does not verify this17.12 asset. Actual Developer ID/TeamIdentifier, notarization/Gatekeeper results, macOS/native-library compatibility and binary versions remain **unmeasured**. Cross-check the observed signing publisher against an authoritative publisher record; do not invent a Team ID from a third-party observation. Any mismatch/rejection stays unresolved and prevents installation/use; no override or signature repair. No claim the bundle is already trusted. After successful review, separately approve isolated tool installation and exact `Contents/Versions/17/bin` version/dependency hashes. Never select `latest`/PG19 or launch the GUI/server during acquisition.

## 3. Owner creates the separate backup key manually

The reviewed [manual command](task53-b1-owner-prerequisites.md#owner-only-manual-key-creation--only-after-approval) is unchanged. When you approve creating it, run this yourself in **Mac Terminal**, not through Codex. Enter a strong unique passphrase interactively and keep it in your password manager. Existing directory/key names cause a stop. Do not send any secret to chat.

```sh
(
  set -e
  set -o pipefail
  umask 077
  cd /Users/rahularutla/Documents/whereto
  B1_KEYS="$HOME/.whereto-backup-v1"
  test ! -e "$B1_KEYS"
  test ! -L "$B1_KEYS"
  mkdir -m 700 "$B1_KEYS"
  /opt/homebrew/bin/openssl req -new -x509 -newkey rsa:3072 \
    -cipher aes-256-cbc -sha256 -days 3650 \
    -subj /CN=WhereToBackupV1 \
    -keyout "$B1_KEYS/recovery.pem" -out "$B1_KEYS/recipient.pem"
  chmod 600 "$B1_KEYS/recovery.pem" "$B1_KEYS/recipient.pem"
  /opt/homebrew/bin/openssl x509 -in "$B1_KEYS/recipient.pem" -pubkey -noout |
    /opt/homebrew/bin/openssl pkey -pubin -outform DER |
    /usr/bin/shasum -a 256
)
```

Share only the final64-character **public SPKI fingerprint** and confirmation that permissions/custody are established. To recheck it later, rerun only the final three-command public-certificate pipeline; it never reads the private key. Private PEM is passphrase-encrypted AES256CBC; backup data still uses existing authenticated CMS AES256GCM/RSA-OAEP SHA256. Never reuse the frontend Ed25519 key. No genuine key was inspected/generated during preparation.

## Recovery custody and the later single B1 job

Choose a trusted recovery custodian and, before cloud recovery, a separately named read-only recovery operator. Deletion can remain unassigned. Keep a protected encrypted private-key recovery copy/passphrase recovery procedure, trusted ciphertext hashes and at least one verified ciphertext copy **outside this GCP project**. Record identities privately; no private key/passphrase in Git, images, GCS or deployment secrets. IAM enrollment and real data download remain separately approved. This is independent of the still-required financial-witness administrator.

After G2-W, verified/installed tools, recipient fingerprint, recovery identity/custody and exact operator enrollment are complete, request:

> Authorize one B1 application-only backup job: existing protected operator, at most3 source sessions sharing60seconds total, direct IPv6/verify-full TLS,2s connection timeout and250ms initial dump-lock wait; exact before/dump/after baseline and six whereto tables with source RLS/grants preserved, no writes or migration. Application1500ms/250ms deadlines unchanged; accept only the already reviewed backup-operator timeout scope. Authorize up to four ciphertext object uploads (64MiB combined) using the enrolled writer and separately authorized independent download of those exact server generations; zero retries/fallback/overwrites. Authorize owner-manual decryption and one fresh local FileVault-protected isolated PG17 Unix-socket restore with exact data/schema/RLS/grants/dependency comparisons and scoped temporary cleanup. Stop on drift/failure. No platform/Vault/Auth/Storage secret export, financial or witness restore, provider calls or new grants.

This is a **future proposed request**, not current authority. B0/G1 and consumed scopes are not reusable. No platform-complete recovery claim; `public.rls_auto_enable` and extension dependencies retain their current refusal gates. Existing B1 source/deadlines/crypto/comparators and historical evaluation evidence stay unchanged.
