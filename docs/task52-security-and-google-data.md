# Task 52 — container patch review and Google identifier retention

Date: 2026-11-16. Baseline: `0f9ebcbaa4ee20bf5afb6901631221101658e073` (clean main). [Machine evidence, exact six candidate image IDs, scanner identity and all retained findings](task52-security-and-google-data-verification.json).

## Engineering result

Implemented a factory-only, encrypted **Place-ID-only** cache on the existing Redis connection/SQL source checks, plus the official Google Maps logo in existing cards/View Plan. This is not a native planning checkpoint and cannot authorize or reconstruct provider work. No new service, database, financial policy, endpoint, model or provider enrollment was added. Real-provider shared recovery and startup remain disabled. The original retention-review contract remains unchanged; this report narrowly supplements its identifier row.

**Zero critical/high findings were remediated.** Compatible vendor patching was investigated rather than pretending an unchanged rebuild fixes them. Six functional candidate images were built and checked, but are not security-approved deployment images. Private real-provider deployment remains blocked.

## Container investigation and disposition

All six old baseline images and all six functional candidates were scanned with the same pinned Grype image and one unchanged vulnerability database: schema v6.1.10, built `2026-11-16T06:30:54Z`. The record includes the exact database archive/checksum, raw scan hashes and package/advisory comparison. No filters or suppressions. Each Python role remains **3 critical / 86 high**; frontend remains **2 critical / 53 high**. All 89 distinct package-version-advisory rows (32 advisory IDs) are retained; none introduced or removed. One explicit identity conflict remains: Grype associates CVE-2026-76844 with zlib1g while its current description and Debian page describe webpack-dev-middleware (NOT-FOR-US). The earlier zlib reachability assessment is not current proof; this match is retained without suppression, pending scanner/vendor correction or independent disposition. Many rows are the same source-package advisory repeated across binaries/roles, not separate proven exploits.

Checked official Docker Hub metadata and signed Bookworm APT metadata in a disposable container without installing packages. Python 3.12-slim-bookworm is still the existing digest `935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df`. Node 24-bookworm-slim now points to the exact 24.22.3 candidate already tested in the purchase checkpoint; it removed zero matches, so that failed experiment was not repeated or promoted. Checked package candidates (glibc, SQLite, PAM, Kerberos, libtasn1, zlib, Perl, gzip, ncurses, GCC runtime, util-linux and ACL) remain their installed versions. No locks, Dockerfile bases or dependency versions changed.

Key official vendor results:

| Advisory | Installed Bookworm version | Current vendor disposition | Action |
| --- | --- | --- | --- |
| glibc CVE-2026-5450 | 2.36-9+deb12u14 | vulnerable; fixed Trixie 2.41-12+deb13u4 | No compatible Bookworm binary found |
| SQLite CVE-2025-7458 | 3.40.1-2+deb12u2 | vulnerable; fixed Trixie 3.46.1-7+deb13u2 | No compatible Bookworm binary found |
| PAM CVE-2025-6020 | 1.5.2-6+deb12u2 | vulnerable; Trixie 1.7.0-5 fixed | Incorrect old patch status is not a fix |
| Kerberos group | 1.20.1-2+deb12u5 | affected Bookworm rows retained; some also affect Trixie | Major-base change would not guarantee zero findings |
| libtasn1 CVE-2025-13151 | 4.19.0-2+deb12u1 | vulnerable Bookworm | No-DSA is not acceptance |

Each remaining package/version, CVE, scanner fix state, current official Bookworm/Trixie row, application-use assessment and uncertainty is in the machine record. Prior reachability assessments are preserved as assessments, not independent exceptions. Non-root/read-only/capability restrictions reduce some attack prerequisites but do not fix vulnerable native code or protect against all data disclosure/RCE. Future provider credentials and private evidence increase impact. No exploitation has been established; no safety certification is inferred.

A supported minimal runtime was investigated: current [Distroless documentation](https://github.com/GoogleContainerTools/distroless) maintains Debian 13 tags; Debian 12 is deprecated. Switching silently to an unmaintained minimal base is not an improvement. A **separate approved Debian 13 compatibility candidate preserving Python 3.12/Node 24**, or a supported vendor Bookworm backport, is the smallest concrete security follow-up; it needs full ABI/import/image/functional verification and may leave advisories requiring independent disposition. No major OS switch was made in this checkpoint.

Fresh npm audit: eight moderate matches, zero high/critical (seven development-tooling matches plus [GHSA-mfr8-8qww-v76h](https://github.com/vercel/next.js/security/advisories/GHSA-mfr8-8qww-v76h) against Next 16.4.2). The latter concerns use-cache functions called through unstable_cache; no such application calls were found. This is a limited source assessment, not a risk exception. Vendor patch 16.4.5 is available; a compatible Next patch cohort is separate; no broad audit-fix/force update was run. Production dependency tree and Python dependency consistency pass.

## Actual Google data path and boundaries

Existing `places_transport`/`routes_transport` and `provider_responses` parse Search/Matrix replies into venue facts, route evidence, ordinary planner results and cards. Names, coordinates, type/activity evidence, route status/duration and credits are needed to resume those results exactly. IDs alone cannot establish those facts. User source/confirmed user controls and derived session/financial identifiers are separate from provider content; derived metadata must not conceal embedded Google facts.

[Places policy](https://developers.google.com/maps/documentation/places/web-service/policies), [Routes policy](https://developers.google.com/maps/documentation/routes/policies) and [service-specific terms](https://cloud.google.com/maps-platform/terms/maps-service-terms) were checked. They explicitly exempt Place IDs from caching restrictions. Conditional coordinate exceptions do not establish a general response-cache permission. Applicable account agreement/billing jurisdiction remains unverified; no legal certification is invented.

| Data | Implemented handling |
| --- | --- |
| `places.id` / permitted Place-ID references | Explicit strict typed identifier projection; encrypted optional cache, at most 100 IDs,1–256 ASCII URL-safe characters each |
| Names, addresses/components, types, hours/prices/ratings, credits, raw Search response | Not admitted to the new cache or native real shared evidence; transient parsing/display only where permitted; no SQL/log/backup response archive |
| Coordinates | Denied by the new cache, despite conditional 30-day exceptions; no unnecessary geometry persistence |
| Matrix status, duration, distance, legs, derived candidate/card results | Full persistent recovery remains refused; do not relabel real data synthetic |
| Google/third-party attribution | Request-local card credits; official unmodified local logo asset; no provider fetch for attribution |
| User-entered source/preferences and protected financial/replay metadata | Existing source/privacy/accounting rules unchanged; no Google content masquerading as application metadata |

`backend/google_retention.py` defines `GoogleReferences`, the explicit `references_from_search` projection and `ReferenceCache`. `EvidenceRedis.references` is available only with the installed factory port and the same store/evidence object. It reuses authenticated encrypted Redis/CAS/capacity bounds and current SQL source/revision/fence/expiry plus external epoch checks before/after I/O. The ID payload is AES-GCM ciphertext; source metadata is bound through associated data, not copied into a plaintext Redis header. Key identity/environment/epoch are checked. Absolute expiry is **min(original SQL expiry, trusted Redis time + 10 minutes)**, create-only; reads never extend it. Factory-owned `forget` expires only the captured key and removes its size/index entries. Revocation blocks reads immediately; it never deletes SQL charges or consumed history. No new Redis ACL command was required.

This cache is not registered as native evidence. `require_checkpoint` always refuses and the existing real-evidence serializer still refuses full real graphs. Missing/corrupt/stale data does not cause a provider refetch, reconstruction, retry or refund. Real Redis enrollment/backup remains off. A future enrolled Redis must exclude these records from backup/export; stale encrypted snapshots remain expired/revision-bound, not continuation authority. Loss of identifiers is safe refusal. Full cross-worker real-results continuation remains contractually blocked until all required retained facts are permitted; dropping names/routes would be unsafe.

Current published policies explicitly mention point-in-polygon restrictions. The actual `venue_geography.py` implements address-component and haversine radius checks, **not a polygon implementation**. Its precise geographic filtering and derived itinerary use still need confirmation under the applicable agreement; no violation or exemption is invented and no location constraint was relaxed to dodge the issue. Required public Terms/Privacy and third-party attribution obligations also remain activation gates.

## Attribution implementation and browser result

`GoogleCredits` uses the official downloaded SVG, embedded unchanged in a local data asset with source URL/SHA256. It renders 98×18px with the required clear space and accessible `Google Maps` label, alongside deduplicated safe third-party links. The existing always-visible card-level credits cover expanded View Plan within the same card. No new Details/photos/Enterprise request is enabled. Unknown hours/prices/availability remain unknown.

Actual local Next.js/FastAPI browser flow exercised interpretation → confirmed authored origin → ordinary generation → three provisional cards → View Plan, at 1280×900 and 390×844. Logo and authored third-party credits were visible; mobile document width remained 390px. These were **authored offline provider fixtures, not real Google venues/routes/model results**. The legacy card's “real venues” mode label is not live-provider evidence. No private hosted IAP/restart/outage browser pass is claimed. Screenshots/logs are local `/tmp/task52-security-retention`; no provider secrets or private evidence were committed.

## Verification and acceptance limits

- Focused backend/provider/admission/dispatcher/projection cohort:175 passed,0 failed/errors/skips.
- New encrypted Redis/restricted PostgreSQL cases:3 passed, covering rejected extra fields, encryption, missing/corrupt/wrong-key records, fixed TTL/no renewal, stale revision, revocation, exact deletion and unchanged gross charges. Source hashes stayed fixed during the final run.
- Frontend:324 passed,1 failed,0 skipped. The unchanged expired-date Surprise fixture still expects200 but receives422. No historical fixture was repinned. The earlier run had a second expected old-text branding assertion; that ordinary UI assertion now verifies the official logo. Focused attribution cohort:8 passed.
- Packaging/artifact tests:9 passed. TypeScript, ESLint, pip check and production npm tree passed. Six actual Linuxamd64 images built (including production Next build); all non-root/read-only/no-capability/source-inclusion checks passed. All refuse missing authorization with exit78. Twelve final-image scans completed; no C/H reduction.
- Existing financial cohort: 30 passed,0 failed/errors/skips,875.686 seconds. Separate operational/witness snapshot rollback and DB/worker restart drills passed, quarantining restored grants and retaining exposure; Redis loss refused reconstruction. This does not explain earlier historical generic refusals/hosted-restart uncertainty. Fresh configured-secret scan:0 matches; original journal/324-file/source-pin check passed read-only. Exact original 126 volumes preserved, 0 running containers, native fixture servers stopped and task Colima profile returned to stopped state. Logs/hashes and development failures are recorded in the machine record. No full-backend or immutable evaluator replay pass is claimed. No live provider, account, hosted networking/IAM or real restore acceptance was attempted.

The functional identifier/attribution changes can be retained independently of the unresolved deployment risk. Image source cohorts and the disabled review draft were regenerated for changed code; historical evaluator manifests, original retention review, base digests, locks, protected SQL, saved RLS, prompts and ordering policies were not changed. Ten paid attempts, 324 private files, accounted $0.047366625, remaining $11.952633375 and persistent halt verify unchanged.

## Exact remaining real-deployment blockers

Security: no compatible C/H fix was available; obtain an approved OS-major candidate test or supported patch/independent residual disposition. Data: identifiers are permitted but cannot restore planner facts; confirm applicable terms for necessary content/derived use or keep real restart continuation closed. Existing external model qualification/price-count policy, transport/credential review, explicit provider grant, Redis regional quote, Supabase capacity/concurrency with unchanged deadlines, independent witness custodian, IAM/IAP/secrets/migration/tester enrollment and infrastructure spending decisions remain unchanged. No purchases, grants, deployment or Task53 follow automatically.
