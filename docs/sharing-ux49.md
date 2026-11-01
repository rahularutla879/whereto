# Tasks 46/49 — shared links and final UX refinements

November 1, 2026. Continues `223a16d`. Tasks 50 and 50A–50E remain unstarted.
No database migration, role/RLS/TLS change, ranking rewrite, new provider API,
Cloud quota change, billing change or new dependency.

## Official websites

The Enterprise mask already requested `websiteUri`; normalization, serialization,
proxying and saved-card state retained the field. Both URL validators accepted only
HTTPS, so a provider-returned HTTP website disappeared while its phone survived.
They now accept provider-returned HTTP/HTTPS external website links, independently
of phone availability. They reject unsafe schemes, credentials, missing hosts,
invalid ports, control characters and oversized values. Links use noopener/noreferrer;
the app does not fetch the website. Maps URLs retain their separate HTTPS/host
allowlist. A missing website produces no invented fallback or broken link.

The old screenshot's response was not retained. We cannot establish whether that
specific venue returned HTTP, no website, or another invalid value without another
live call; no such call was made. Fixture tests establish the HTTP validation defect,
not the historical venue's exact response. The visible label is **Official website**.

Automatic opening remains Pro-only. The explicit phone/website choice retains the
existing Enterprise gate and exact field mask. Both/phone-only/website-only/neither,
HTTP/HTTPS/unsafe URLs, two stops with different availability, partial failure and
Pro followed by Enterprise are covered with invented responses.

## Sharing without a per-token provider quota

Saved-plan access and provider enrichment are separate. Valid capabilities still
read only their original selected plan under existing expiry and RLS rules, even
when provider admission fails. Other saved alternatives are retained internally.

The six-attempt **per-capability** 30-minute session has been removed. Each explicit
open or manual update is a fresh bounded action with at most four unique selected
references. This reuses the existing outing budget without accumulating a permanent
provider allowance on a sharing token. The generated-outing contact budget remains
six; saved actions cannot dispatch more than four. No unrestricted response cache,
background retry, queue or new fan-out was added.

A locked replay registry stores only `(capability hash, action UUID)` and monotonic
creation time: 30-minute expiry, maximum 512 entries. Same-action replay makes no
additional dispatch. At capacity it fails closed with a known expiry estimate.
Wholly rejected pre-admission actions release their marker and charge no attempts;
any admitted action retains its marker, including partial/provider failures. Restart
clears in-process replay metadata, while the persistent usage ledger remains intact.

Shared safeguards remain: **ten Details/minute**, **one concurrent provider request**,
process/application ceilings where configured, durable locked ledger admission and
actual Cloud quotas. A new capability or process restart cannot bypass the persistent
minute ledger or Google's daily quota. Provider attempts, including dispatched
failures, remain conservatively counted. Existing development exploration has a
nonblocking estimated-cost warning; normal-mode spending protection is unchanged.

### Ten-viewer evidence and limits

Offline simulated viewers of one two-stop plan, spaced 13 seconds apart, all
received both original venue identities: 20 Details attempts, no alternatives,
no provider cache. Ten simultaneous viewers are deliberately not all admitted:
one occupied the provider slot, nine received a safe busy result and retained the
saved structure. Five immediate two-stop opens consumed the shared ten/minute;
the sixth was blocked by that shared boundary and recovered after the simulated
window expired. Two-link concurrency, multiple opens/tabs, UUID replay, process
restart with persistent ledger, Cloud quota, authentication, partial success,
invalid/expired access and failed pre-admission are covered offline.

This does **not** promise instant enrichment for ten simultaneous friends. Twenty
requests require at least two available minute windows. The last independently
verified Cloud Details ceiling is 40/day; actual remaining Cloud allowance was not
queried or changed. That ceiling could support at most twenty two-stop Pro opens
in a day if no other Details requests consume it. Contact updates consume more.
The app remains a trusted **localhost development** application, not a publicly
reachable sharing deployment. Public deployment and broader abuse/auth protections
remain later roadmap work; this repair does not loosen development guards.

At the published first paid global tier, 20 Pro requests cost **$0.34** before free
allowances; the unchanged conservative local estimate reserves **$0.40**. Twenty
explicit Enterprise requests would cost **$0.40** before allowances. No owner ledger
was reset. Actual Google requests and charges in verification: **zero**.

[Places policies](https://developers.google.com/maps/documentation/places/web-service/policies)
permit storing Place IDs, not unrestricted permanent Places content. Current names,
addresses, contacts and attributions stay in component memory, never SQL or browser
persistent storage. [Details fields](https://developers.google.com/maps/documentation/places/web-service/place-details)
and [pricing](https://developers.google.com/maps/billing-and-pricing/pricing) were
reviewed. [Places UI Kit](https://developers.google.com/maps/documentation/javascript/places-ui-kit/get-started)
requires additional browser/API-key/service setup and has its own billed operation;
it was not activated. A costed future choice requires owner review: compare an
approved UI Kit architecture or explicitly revised project capacity against current
20-Pro-request/$0.34 ten-view cost. Neither removes shared provider limits by itself.

## Product UI and diagnostics

The normal homepage contains no Local development tools disclosure, raw snapshots
or cost counters. Instrumentation remains on **http://localhost:3000/dev/diagnostics**.
The server page, API proxy and existing Python boundary enforce development/local
access; the production page and API return 404. Forwarded, remote-host and foreign
Origin requests are denied. Snapshots retain aggregate allowlisted counters/timings,
not provider responses, exact locations, credentials or capability tokens. Loading
or reloading diagnostics makes no Google requests.

Activity follow-ups link **View supported activities** in a secure new tab to
**http://localhost:3000/supported-activities**. Content derives from the shared
`data/mock-venues.json` activity catalog, also consumed by Python; a regression
checks exact correspondence with `ActivityType`. Existing event metadata provides
the two groups, rather than a separate copied list. Open-ended venue requests are
explicitly non-exhaustive. Sports match venues do not imply playing/training,
verified sessions or tickets. No provider call is needed for the page.

The original request and follow-up remain in the first tab. One labeled question
replaces the duplicated aggregate explanation. Only the follow-up has Continue
planning while answers are requested; location/date questions do not show the
activity link. Empty follow-ups do not display an irrelevant Before you go notice.

For flexible over-preference cards, the specific verified travel deviation remains;
equivalent `extra_first_travel`/`extra_between_travel` generic warnings are suppressed
only when a specific deviation exists and the issue is not a violation. Independent
accessibility, missing evidence and hard-limit warnings remain. No feasibility or
ranking rule changes. A group renders one heading and one paragraph, using the
requested flexible copy. Mixed, unverified and explicitly opted-in hard exceptions
receive accurate separate wording. Page history preserves the same presentation.

## Verification

- Full backend: **633 run, 615 passed, 18 hosted checks skipped**, 169.373s.
- Full frontend: **215/215 passed**, final rerun 116.692s. Focused frontend **9/9**, 6.787s. TypeScript, ESLint, production build
  and Python dependency check passed. Focused backend rerun: 50 run, 43 passed, seven hosted skips.
- Authorized hosted run: **35/35**, including **18 actual PostgreSQL rollback tests
  and 17 offline checks**, 17.884s. Read-only schema/grant/ownership/RLS/ledger check passed.
- Browser verification uses the real restricted PostgreSQL runtime, invented Google
  fixtures, an isolated cost ledger and a blocked real Google transport. A committed
  option-2/two-stop plan reopened in a native new tab with automatic Pro information;
  explicit contact loading displayed HTTP Official website plus two independent
  phones. Original generated three-card page stayed intact. Copy-success feedback,
  registry reference new-tab context, local diagnostics and production/forwarded
  denial were observed. Show different options/Explore farther retained page history.
- Desktop 1280 and mobile 390 widths are checked against DOM scroll width and actual
  screenshots. No horizontal overflow in the checked saved-plan view. Keyboard
  focus and labeled activity follow-up were checked; no full assistive-technology audit.
- Exact hash-scoped browser fixture removed and independently verified committed; other owner plans preserved, two migrations unchanged. Normal real-profile backend restored, backend/frontend health 200, restricted authenticated TLS checker passed. Explicit mock reported all provider gates off. Temporary servers/tabs stopped and test link forgotten. Final secret/full diff review passed.
