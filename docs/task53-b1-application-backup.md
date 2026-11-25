# B1 application backup — proposed, not authorized

Current v2 corrections and owner prerequisites: [tool/key/folder decisions](task53-b1-owner-prerequisites.md). Original v1 evidence is retained; do not execute its literal `--file=-` command.

**Coverage:** the six `whereto` tables (`plans`, `plan_constraints`, `generated_itineraries`, `itinerary_stops`, `source_metadata`, `schema_migrations`), all schema objects, data, 13 observed indexes, constraints, triggers, RLS definitions/flags and object grants. Archive safe role attributes/membership metadata without passwords or role settings. No new financial schema existed at B0: one appearing before export stops this scope. This is an **application recovery baseline**, not a full Supabase platform backup.

`public.rls_auto_enable` stays outside the application dump. Its body/provenance has not been inspected. The proposed [baseline SQL](../deployment/sql/b1-application-baseline-readonly-v2.sql) checks catalog dependencies; any reference outside `whereto`/`pg_catalog`, new routine/type/sequence, missing table or owner/ACL drift stops for review before export. Event-trigger/platform behavior is not reproduced. Installed `pgcrypto`, `uuid-ossp`, `pg_stat_statements` and `supabase_vault` are not automatically exported/installed; reviewed migrations use core `gen_random_uuid()`. Dependency or restore errors must stop, not silently omit objects. Auth/Storage/Realtime/Vault contents, Storage files, dashboard settings/API keys, extension binaries, external keys and saved-link capability secrets are excluded. The historical evaluation journal is untouched. Existing source role settings are excluded because they can contain secrets.

## Owner decisions before execution

1. **Key:** select a new backup-only RSA-3072 recipient using the installed `/opt/homebrew/bin/openssl`4.1.0. AES-256-GCM CMS with RSA-OAEP/SHA256 is supported by [official OpenSSL documentation](https://docs.openssl.org/4.0/man1/openssl-cms/). No genuine owner key was created; only disposable test keys were used. No host package installation command was run. Separately approve owner-manual key creation; use an encrypted private PEM,0700directory/0600files, passphrase entered interactively, and an independent recovery copy. Never use the frontend Ed25519 key. Pin the public certificate/SPKI fingerprint; private material never goes into chat/Git/cloud backup.
2. **Off-site:** recommend a dedicated folder in your existing iCloud Drive. You reported3.3GB available; automated quota inspection was unavailable. Folder creation remains unapproved;300MiB is a planning budget, not a provider reservation. Apple provides [5GB free shared storage](https://support.apple.com/en-us/108922); account usage/sign-in were not inspected. Incremental cost$0 only if existing quota suffices. Allocate300MiB; keep the latest3 verified generations plus1 pre-change generation (each complete generation, including all ciphertext/receipts, <=64MiB). No automatic deletion: never remove the last verified copy before its replacement passes off-site recovery. Keep ciphertext hashes/receipt separately with the recovery custodian; encryption alone does not authenticate who uploaded a file. A local synced folder alone is not off-site proof: independently download the actual cloud copy.
3. **Tools:** native PG17 tools remain absent. The existing Colima/cached PG17.11 fixture passed and was returned stopped, with all pre-existing resources preserved. The VM has no IPv6 default route, so it is not a proven live-export client. Prefer the self-contained official PG17.12 Postgres.app bundle after separate acquisition/signature/hash/version approval; no Homebrew/PATH changes or GUI/server startup. [Current owner prerequisites](task53-b1-owner-prerequisites.md). Native locale/live Supabase compatibility remains untested.
4. **B1 authority:** approve the existing protected operator credential (B0 confirms `postgres` has BYPASSRLS), exact application-data/schema export and private baseline reads, quiet/no-DDL/no-write window, encryption recipient/destination/retention, local FileVault-protected temporary restore, and owner-manual private-key decryption. Also approve a **single60-second total source/export scope**,250ms initial dump-lock wait, zero retries. pg_dump resets its own timeouts; application SQL deadlines remain1500/250ms. No new API keys, grants, witness restore or platform changes.

## Exact commands for the approved operator — do not run now

Work from `/Users/rahularutla/Documents/whereto`. First pin the binaries, public recipient, reviewed files and output generation. A future approved runner loads only the existing operator configuration into private child memory: direct host bound to P1's hash, one selected IPv6 address,5432,`postgres` database/operator, verify-full CA and2s connect timeout. Never source a shell file or put passwords in argv/logs. No pooler or elevated fallback. Across the three stages use one common monotonic60s deadline and at most3 source sessions, not60seconds per stage.

```sh
"$B1_PG_BIN/psql" -X -qAt --no-password --set=ON_ERROR_STOP=1 \
  --file=deployment/sql/b1-application-baseline-readonly-v2.sql
"$B1_PG_BIN/pg_dump" --format=custom --schema=whereto --strict-names \
  --lock-wait-timeout=250ms --no-password
# Repeat the exact baseline command once after the dump, within the same scope.
```

Each stdout stream goes **directly** to the following encryptor, with exclusive `.partial` output and promotion only after both exits succeed. [Bounded pipe code](../deployment/b1_pipeline.py) enforces the remaining deadline, kills both process groups on failure, rejects any stderr without logging contents and refuses existing generations; it loads no credentials and has no execution CLI. It is not authorization or a complete enrolled live runner. Baseline facts must be privately validated before starting the dump. Safe role metadata and baseline digests are encrypted alongside the archive, never published in Git. Reject the complete generation if combined ciphertext/receipt size exceeds64MiB; the helper also caps each individual output. Do not use `pg_dumpall` (unrelated roles/role settings) or `--enable-row-security`, `--no-owner`, `--no-acl` or `--disable-triggers`. [PostgreSQL documents](https://www.postgresql.org/docs/17/app-pgdump.html) that schema selection omits outside dependencies and default RLS handling refuses incomplete exports.

```sh
/opt/homebrew/bin/openssl cms -encrypt -binary -stream -outform DER \
  -aes-256-gcm -recip "$B1_RECIPIENT_CERT" \
  -keyopt rsa_padding_mode:oaep -keyopt rsa_oaep_md:sha256 \
  -keyopt rsa_mgf1_md:sha256
```

Reject any failure, warning, changed baseline, dependency drift, missing role authority, overflow or uncertain completion. No automatic resume/retry. Archive ciphertext hashes/sizes, source/tool/query/recipient identities and explicit exclusions in an owner-only receipt; upload only successful ciphertext. No raw rows or dump logs leave the protected stream.

## Disposable PG17 restore and objective acceptance

After separate restore/private-key approval, use an exclusive0700directory under `/private/tmp`, **not** a synced directory. FileVault is currently On. Plaintext archive and fixture data are temporary local files on that encrypted volume; this is an explicit B1 approval item, not a promise that plaintext never exists. Preserve source snapshots. Use a fresh `b1_restore_admin` cluster, Unix sockets only and the approved source locale/encoding. No source credentials or PG environment enter the restore processes. Stop on unavailable locale, dependency mismatch or role collision. Never use the source host or an existing database as the target.

```sh
# Owner performs this decryption interactively; no passphrase argument/environment.
/opt/homebrew/bin/openssl cms -decrypt -binary -inform DER \
  -in "$B1_DOWNLOADED_CMS" -recip "$B1_RECIPIENT_CERT" \
  -inkey "$B1_BACKUP_PRIVATE_KEY" -out "$B1_WORK/application.dump"
# Check exit=0 and trusted ciphertext receipt BEFORE any pg_restore. Decryption
# may emit partial plaintext before authentication fails; never pipe into restore.
"$B1_PG_BIN/initdb" -D "$B1_WORK/pgdata" -U b1_restore_admin \
  --auth-local=trust --auth-host=reject --encoding=UTF8 --locale="$B1_APPROVED_LOCALE"
"$B1_PG_BIN/pg_ctl" -D "$B1_WORK/pgdata" -l /dev/null -w \
  -o "-c listen_addresses='' -c unix_socket_directories='$B1_WORK/socket' -c unix_socket_permissions=0700 -c log_min_error_statement=panic -c log_error_verbosity=terse" start
"$B1_PG_BIN/createdb" -h "$B1_WORK/socket" -U b1_restore_admin -T template0 whereto_b1_verify
"$B1_PG_BIN/psql" -X -q --no-password --set=ON_ERROR_STOP=1 \
  -h "$B1_WORK/socket" -U b1_restore_admin -d whereto_b1_verify \
  --file=deployment/sql/b1-fixture-roles-v1.sql
"$B1_PG_BIN/pg_restore" --list "$B1_WORK/application.dump"
"$B1_PG_BIN/pg_restore" --exit-on-error --single-transaction --no-password \
  -h "$B1_WORK/socket" -U b1_restore_admin -d whereto_b1_verify "$B1_WORK/application.dump"
```

These are review commands, not a safe copy/paste batch: the approved wrapper must assert the fresh path/Unix socket, create the0700socket directory, set umask077, privately inspect archive scope/SQL before restore, enforce bounded child deadlines and suppress raw error output. Fixture role SQL is guarded against a live destination. Verify source safe role attributes before using it; NULL passwords are intentional. Supabase's administrator membership graph is archived as metadata but **not recreated** locally. Existing role/password/managed-control recovery is outside application-fixture certification.

Pass only if source before/after and fixture have equal **six exact table counts + SHA256 content digests; schema/index/constraint/trigger/default/RLS fingerprints; application owners/object grants/runtime attributes**; all six RLS flags remain enabled/forced; uncredentialed runtime cannot see saved-plan rows. Sequence count must remain zero or this scope stops. Compare relevant baseline facts, not database name/version strings or excluded managed administrator edges. Missing policies/permissions, unknown dependencies, warnings, locale drift or unsupported extensions fail. Baseline v2 has run on the disposable PG17.11 fixture only, never on Supabase. Fictional-only encrypted dump/restore now passes with cached PG17.11; no live dump/restore, native Mac tool or genuine key has been tested. Independently download and test the off-site copy before declaring a recovery point. Stop only the exact task-owned fixture afterward; deletion requires approved exact-path cleanup, never a broad prune.
