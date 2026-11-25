# B1 owner prerequisites — no live export approval

**Storage:** the owner superseded iCloud with Google Cloud Storage. Do not create the previously proposed iCloud folder. The earlier 3.3GB owner statement remains historical only. Use the [GCS destination proposal](task53-b1-gcs-backups.md); no bucket, IAM, upload or live B1 authority exists. Recovery/deletion custodians are not selected and no identity is assigned.

**Tools:** fictional encrypted dump/restore passed with the cached PG17.11 image, without pulling/building images or changing Homebrew. Existing Colima was started/stopped; guest emulators/context registration occurred during startup, and stop removed the context. All135 volumes,82 cached image IDs and the original default Docker selection were preserved; no test containers/volumes remain. The VM has **no IPv6 default route**: its cached client is not approved for live direct-IPv6 export.

Prefer the official **Postgres.app2.9.7 / PostgreSQL17.12 Universal** bundle, approximately120MB, [listed by its vendor](https://postgresapp.com/downloads.html). This avoids Homebrew dependency changes. Separate approval is needed to download/copy the bundle, verify signature/Gatekeeper and hashes/version, and select its explicit `Contents/Versions/17/bin` tools. Do not open its GUI, start a server, edit PATH, remove quarantine or substitute the default PG19 bundle. No download/install was performed. Actual native locale and Supabase compatibility remain untested.

## Owner-only manual key creation — only after approval

Use a new backup-only key, never the frontend signing key. After explicitly approving key creation, run this yourself in Mac Terminal. Enter a strong new passphrase interactively; keep it in your password manager. Do not send the key/passphrase to chat. Existing directory/key selection stops rather than overwriting anything.

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

Only the final **public fingerprint** may be shared. The recipient certificate is not an owner governance signature or spending approval. Keep an encrypted recovery-key copy and passphrase access with your chosen custodian, outside the ciphertext folder. Store their identity privately; a local custodian reference is sufficient for enrollment—no name/email/private material in Git or chat. Owner-only enrollment can bind the public certificate/SPKI hashes, tool/source hashes, destination, retention and custodian reference. It must leave live B1 authorization absent until separately approved. This does not establish independent witness administration.

## Corrected commands and tested boundary

[Current v2 proposal](../deployment/cloud-run/b1-application-backup-PROPOSED-v2.json) supersedes v1. Preserve v1/e54 evidence. The fictional test proved `pg_dump --file=-` attempts to create a literal `-`; the corrected command **omits that option** and uses default stdout. Baseline v2 canonicalizes effective ACLs (including grantor, grantee, privilege and grantability), because explicit owner-all and NULL/default owner ACLs restore equivalently. Actual added grants or disabled forced RLS still fail. [Workflow commands](task53-b1-application-backup.md).

The local test used disposable test-only encrypted RSA3072 keys and fictional rows. AES256-GCM round-trip, ciphertext tamper/wrong-passphrase refusal, six-table content/schema match, forced RLS, uncredentialed refusal and source-before/after equality passed. Four development failures/diagnostic attempts are retained in verification evidence; no live SQL or genuine owner keys were involved. These checks do **not** prove native Mac PG17.12, real account export, provider content rights or off-site recovery.

## Next exact approvals

1. Review the separate G1 empty-GCS-bucket proposal and cost envelope. Select distinct writer operator, recovery and deletion principals before later G2 IAM enrollment; no data upload yet.
2. Approve the PG17.12 bundle acquisition/verification only, without Homebrew or server startup.
3. Approve owner-manual key creation above, then provide only its public fingerprint and confirm recovery custody.
4. After enrollment/tool/locale checks, authorize **one live B1 job**, at most3 operator source sessions sharing **60seconds total**, direct IPv6/verify-full TLS/2s connection timeout,250ms initial dump-lock wait, zero retries or fallback. Permit exact six-table schema/data/RLS/grants export and baseline reads using the protected operator; application1500/250ms deadlines unchanged. Separately specify upload and genuine-key/local-restore permissions. No key rotation, platform dump, grants, provider calls or correlated witness restore.

Until those decisions are made, no live backup/restore authority exists. Retention remains three verified generations plus one pre-change generation, at most64MiB combined per generation. Coverage is application-only: managed Auth/Storage/Realtime/Vault data, Storage files, secrets/settings, platform administrator graph and unknown dependencies remain excluded/review-gated.
