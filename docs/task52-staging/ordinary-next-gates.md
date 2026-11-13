# Remaining ordinary private-staging gates

This checklist is not provisioning, financial or launch authorization. Parent order remains [P0–P10](IMPLEMENTATION.md).

- [ ] Review the private UI readiness/mode contract. `/api/planning-mode` is still blocked; actual browser interaction is not established by the HTTP/client-driver tests.
- [ ] Verify tab-local handle retention, explicit source-edit invalidation, consumed-turn recovery and user-visible new-request instructions in the existing form. A fresh unlinked request cannot be inferred to replace another tab. No automatic inference retry.
- [ ] Review additional deterministic preference/time/travel controls as separate validated actions before expanding the seven current execution controls. Manual-only planning remains blocked.
- [ ] Investigate unexplained SQL protocol refusals with sanitized reason/SQLSTATE/stack evidence and bounded load tests. Preserve frozen parent tests/pins; the versioned clock adapter does not repair their historical results.
- [ ] Integrate each additional native/public mapping separately: advanced, options, origin lookup, Details, selected saving/reopening and purpose-specific refresh. Preserve independent saved capabilities/RLS and one-use refresh semantics.
- [ ] Complete real IAP/IAM caller/audience/ingress enrollment, proof-key rotation/revocation, restricted Supabase migration, encrypted managed Redis/privacy review and independently operated recovery/backup reconciliation. No synthetic reset/bootstrap script against owner databases.
- [ ] Qualify a hosted LLM independently, implement verified real tokenization/pricing and canonical real provider transports. Obtain explicit finite application spending authorization; no proposed staging amounts or old evaluation allowance are active.
- [ ] Review current image vulnerability residuals, package a reviewed production bootstrap, verify cloud startup without test overrides, enforce private access and record rollback. The current startup guard still refuses.
- [ ] Run browser, latency, quality, two-instance/outage/restore and Mac-off private-staging acceptance under separately approved real usage limits. Public launch remains a separate explicit owner decision.

Next bounded implementation checkpoint: ordinary private UI/edit/recovery compatibility under this handle contract, including a non-billable readiness contract, while keeping unsupported provider workflows closed. Do not start it automatically or begin Task 53.
