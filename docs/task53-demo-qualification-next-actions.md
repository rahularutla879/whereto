# Next demo qualification operations — not execution authority

Baseline `ae54a09dbecb115dfbaf5c24eff7854b89e958d8`. The successful P1 scope is consumed: no repeat preflight, secret read, live SQL or cloud operation occurred here. [Exact inactive bounds and source/SQL hashes](../deployment/cloud-run/demo-qualification-next-scopes-PROPOSED-v1.json).

| Scope | Exact next authorization | What it establishes |
|---|---|---|
| **B0 — backup inventory** | One catalog-only session, at most 30 seconds, using [exact inventory SQL](../deployment/sql/backup-baseline-catalog-readonly-v1.sql), existing restricted credential loader, direct IPv6/verify-full TLS and unchanged 1500/250 ms deadlines. No rows/password catalogs/function bodies, retries or operator fallback. | Owners, ACLs, RLS flags, role membership and managed/extension dependencies needed to select backup coverage. This is a new coverage inventory, not another P1. Output stays owner-only; overflow/limited visibility stops. |
| **B1 — export and disposable recovery proof** | After B0, approve exact schemas/tables and sensitive application-data export, the named encryption public recipient, off-site vault/path/custodian and any charges; separately permit operator credential loading, bounded backup timing and isolated restore. | A recoverable baseline before protected installation. No export/upload/restore is authorized merely by choosing a recipient. |
| **W1 — witness custody** | Name a trusted administrator with their own account/organization and independent backup/restore authority. They separately authorize their Free witness setup and tests. | Independent recovery authority. A second project/password under the operational administrator is insufficient. No paid witness research needed. |
| **N1v6 — amend existing subnet** | Separately authorize the single command below after fresh read-only conflict/policy checks. | Google-assigned external `/64` on the existing subnet. No IAM, N2, IP/NAT purchase or Cloud Run deployment. |

B1 reuses the [existing encrypted backup/restore procedure](task53-free-preflight-backup.md#b1--encrypted-off-site-logical-backup-separately-gated), including schema/data, roles/grants, RLS, sequence state and any approved operational financial history. The encryption recipient must be for encryption, **not** the frontend signing key. No public recipient, off-site destination or independent recovery custodian has yet been selected. No new subscription or key generation is implicit.

Before export, review application-owned versus managed/extension-owned objects. Do not execute an unscoped full-project dump that might include Vault/credential material. Password hashes, API keys, decrypted Vault secrets and local credential files are excluded; exclusions must be explicit in the coverage manifest. Storage object bytes, dashboard/Auth settings, extension binaries and platform encryption keys need separate recovery arrangements. Do not call an incomplete dump a full Supabase backup. PG17.11 is now verified; compatibility of the required extension binaries and managed roles in the disposable restore still needs checking.

`pg_dump` resets its own SQL timeouts. The **proposed**, separately approved backup-operator scope is at most 60 seconds with 250 ms initial table-lock wait and no retry; application/witness 1500/250 ms limits remain unchanged. Keep the source quiet, capture approved schema/ACL/RLS/role baselines and encrypted data counts/digests/sequence values before/after, fail on drift or errors, then prove encrypted off-site download/decryption and a fresh disposable PG17 restore. The existing comparison SQL alone is not complete recovery verification. No live export or restore is authorized now.

## Actual capacity test: what can and cannot run read-only

A two-connection, twenty-transaction saved-plan-role reuse benchmark is bounded in the JSON as **optional and not recommended next**: P1 already passed and this would not qualify absent protected routines. It cannot access app rows or financial history or stand in for the real authority.

**I1 installation and C2 restricted-pool test are separate later approvals.** Existing `SQLPool._check()` calls `private_runtime.connection_identity()`. That function measures real DDL/ACLs and protected policy/configuration. It refuses missing policy. Therefore neither the saved-plan login nor an empty installation can substitute for genuine enrolled model/rate/financial configuration. Do not fabricate a zero-cost policy or fake grant to make the check pass. Exact projected SQL hashes in the JSON are an inventory, **not an install batch**; managed installer privileges and additive DDL still need review after B1/W1. Never run the disposable `test_sql.fixture` or `test_hosted.enroll` on Supabase.

Once genuinely enrolled, **C2** uses the unchanged actual `SQLPool` and nine exact-role pools: factory runtime/issuer, counter, dispatcher on operational PostgreSQL; backend nonce, factory/counter/dispatcher witness and recovery on independently administered PostgreSQL. Pool maximum stays two. One cohort creates at most **8 operational + 10 witness** physical connections, **45 lease checks**, one active query at a time, and at most **120 seconds** total. Populate each two-slot pool, prove third-lease local refusal, then three reuse checks per pool; close all pools on exit. Record connect/contract/lease/cleanup latency, backend affinity and created-connection counts. Stop on the first error, timeout, wrong identity/epoch or evidence conflict; no reconnect/retry/deadline changes. On witness leases, retain the existing epoch and `assert_runtime` checks, including the seven genuine approval references; never insert fictional review rows. Reading configuration/quarantine evidence through those reviewed functions requires explicit C2 authority; P1/B0 metadata permission is insufficient. Do not query or return underlying financial history records.

C2 writes no reservation, INTENT, nonce, ticket or usage record and sends no provider request. It establishes pool/contract overhead only. Existing revision-overlap/operator planning allowances (18 operational/22 witness **plus** platform/current headroom) remain. Actual financial write-path capacity and full demo acceptance require a **later separately authorized single genuine outing**, with model qualification, current rates/count policy, finite grants, credentials, retention/security approvals and independent witness/Redis enrolled. No synthetic financial fixtures belong on the live database.

## Existing N1v6 command — review only

```sh
gcloud compute networks subnets update whereto-staging \
  --project=where-to-512422 --region=us-east4 \
  --stack-type=IPV4_IPV6 --ipv6-access-type=EXTERNAL --quiet
```

Reuse the [unchanged inactive amendment](../deployment/cloud-run/dual-stack-amendment-PROPOSED-v1.json). Google chooses the `/64`; no invented range or N1 replay. Read back IPv4/PGA/IPv6/routes after a separately authorized update. Later broad Run-agent `publicIpAdmin` IAM and actual source allowlisting each need their own approval. N2 stays separate.

**Shortest next owner actions:** authorize B0 only; provide the B1 encryption public recipient/off-site custodian and nominate W1 in parallel. N1v6 may be approved independently to move hosting forward. Keep Free; no purchase is justified yet. Keep the verified $6/month Redis candidate unchanged and unpurchased, with its original post-purchase acceptance gates. No new credentials, grants, provider calls or hosting-risk acceptance follow from this preparation.
