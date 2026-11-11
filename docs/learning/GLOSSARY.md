# Project glossary

Plain-language definitions tied to actual code or a clearly labeled design. For teaching and examples, follow the numbered chapters. A definition is not an instruction to activate a service.

## Abstraction

A smaller interface hiding implementation details. AIProvider lets interpretation ask for an extraction without knowing the transport. [Project source](../../backend/ai/__init__.py).

## Acceptance criteria

Specific observable outcomes required to finish a change; this project requires establishing them before implementation. [Project source](../../AGENTS.md).

## ADC — Application Default Credentials

The backend credential-discovery mechanism used for protected local impersonated Google access. Do not expose its reusable source credentials. [Project source](../../backend/places_transport.py).

## Admission

Permission for bounded work to begin. Local request/inference capacity admission differs from semantic admission foundations and provider spending reservations. [Project source](../../backend/admission.py).

## Admission receipt

A purpose/scope/revision-bound internal validation handle, not arbitrary JSON or a public authorization badge. Its foundation is Python-test scoped, with no-op ordinary guards. [Project source](../../backend/planning_admission.py).

## AI — Artificial intelligence

In this app, a language model extracts requirements. It does not establish venue existence, opening hours or bookings. [Project source](../../backend/ai/ollama.py).

## Algorithm

A repeatable procedure, such as enumerating candidate combinations or scheduling earliest feasible visits. [Project source](../../backend/planner.py).

## API — Application Programming Interface

An agreed way programs request work using paths, methods and data contracts. Browser and Python have corresponding planning endpoints. [Project source](../../backend/main.py).

## Argument

A value passed into a function, such as request passed to generate_plan. [Project source](../../backend/main.py).

## Array / list

An ordered collection. Repeated activities must remain distinct ordered occurrences rather than becoming a set. [Project source](../../backend/journey.py).

## Assertion

A test condition that must be true. It documents expected behavior for the declared fixture. [Project source](../../backend/test_planner.py).

## Asynchronous / async

Work that can suspend while waiting. It does not automatically make blocking CPU/provider work safely concurrent. [Project source](../../backend/provider_work.py).

## Attribution

Required credit identifying provider sources and supplied third-party credits, retained in venue/detail presentation. [Project source](../../components/real-venue-facts.tsx).

## Authentication

Proving an identity, as OAuth authenticates the backend to Google. This differs from permission to spend or view a particular plan. [Project source](../../backend/places_transport.py).

## Authorization

Checking permission for a specific operation. Saved capability membership and RLS are scoped authorization, not user accounts. [Project source](../../backend/saved_plans.py).

## Availability

Whether an activity/session can actually be used or booked. Venue identity and opening hours do not establish seats, courts or tickets. [Project source](../../backend/feasibility.py).

## Await / promise

A promise represents an eventual result; await waits for it or raises its failure. Clients await HTTP before reading/validating JSON. [Project source](../../lib/planning-client.ts).

## Backend

The Python service owning interpretation validation, authoritative planning, provider access and SQL saving. [Project source](../../backend/main.py).

## Beam search

A bounded search retaining only a limited set of promising partial paths. The advanced planner uses a width of 24 initially rather than exhaustive route optimization. [Project source](../../backend/advanced_routing.py).

## Bearer capability

An unguessable secret whose possession grants a scope. Anyone with a valid saved link can read it until expiry. [Project source](../../backend/saved_plans.py).

## Boolean

A true/false value. A configuration flag states a choice; it does not prove infrastructure exists. [Project source](../../backend/admission.py).

## Branch

A Git name for a line of commits. Creating one does not isolate pre-existing dirty working files. [Project source](../../AGENTS.md).

## Budget

A scoped cap or accounting allowance. Per-person money, group money, inter-stop travel and whole-trip time cannot be substituted for one another. [Project source](../../backend/models.py).

## Cache

Reuse of previously computed evidence within allowed scope/freshness. Current route evidence is mode-bound and under five minutes old. [Project source](../../backend/routes.py).

## Callback

A function passed to another operation, such as onClarification updating page state. [Project source](../../app/page.tsx).

## Candidate

A possible assignment of venues to required occurrences before complete feasibility/ranking. [Project source](../../backend/planner.py).

## Canonicalization

Converting equivalent representations into one stable form. Request fingerprints canonicalize JSON key order/whitespace, not user meaning. [Project source](../../backend/admission.py).

## Capacity

A bound on simultaneous work, such as 16 admitted request readers/work owners. It does not mean verified venue group capacity. [Project source](../../backend/admission.py).

## CDN — Content Delivery Network

Proposed distribution of cacheable static frontend assets. Private planning APIs still require controlled access and no-store responses. [Project source](../../docs/task52-cloud-architecture-evaluation.md).

## Clarification

A question resolving missing or ambiguous information without inventing constraints or dropping stops. [Project source](../../backend/interpretation.py).

## Class / instance

A class defines a kind of data/behavior; an instance is one value created from it, such as a PlanningRequest. [Project source](../../backend/models.py).

## Client

A requester, usually the browser. Client data remains untrusted even when the interface originally produced it. [Project source](../../lib/planning-client.ts).

## Cloud Run

The proposed managed container hosting service for Next.js/FastAPI. It is not deployed by the checked-in proposal. [Project source](../../docs/task52-cloud-architecture-evaluation.md).

## Commit / HEAD

A Git commit records a file snapshot and parents; HEAD selects the current commit. Handbook started at a7ed106 and was reconciled with independent offline V5 commit b1efe96. [Project source](../../HANDOVER.md).

## Component

A reusable React interface function taking props and describing elements; PlanCard presents plan data. [Project source](../../components/plan-card.tsx).

## Concurrency

Overlapping work in time. Shared locks/admission prevent particular races; current process-local state does not coordinate a cloud fleet. [Project source](../../backend/admission.py).

## Connection pool

A bounded reusable set of database connections, proposed for cloud fleet operation. Current saves use bounded one-connection transactions. [Project source](../../docs/task52-cloud-architecture-evaluation.md).

## Constraint

A requirement limiting allowed results. Preferences rank eligible results and cannot silently override hard constraints. [Project source](../../backend/models.py).

## Container / image

An image packages application/runtime files; a container runs that package. Cloud deployment packaging remains future work. [Project source](../../docs/task52-production-implementation-plan.md).

## Context window

The model input/output context capacity configured by num_ctx, distinct from a user outing time window. [Project source](../../backend/ai/ollama.py).

## Contract

An allowed data shape plus rules at a boundary. Pydantic fields and validators define Python contracts. [Project source](../../backend/models.py).

## Correlation ID

A safe generated reference joining observations for an operation without revealing its private request. [Project source](../../backend/failures.py).

## CSRF — Cross-Site Request Forgery

An unwanted browser action induced from another site. Protected local proxies check host/origin/forwarding conditions. [Project source](../../lib/persistence-proxy.ts).

## CSS — Cascading Style Sheets

Rules controlling layout/appearance. Tailwind utilities coexist with actual project CSS. [Project source](../../app/globals.css).

## Database

Durable organized data storage; this project saves normalized private selections in PostgreSQL. [Project source](../../backend/migrations/0001_initial_planning.sql).

## Decimal

Base-ten arithmetic used to compare exact supplied money and elapsed bounds without binary floating-point boundary errors. [Project source](../../backend/ranking.py).

## Deduplication

Removing duplicate identities while preserving legitimate repeated categories/occurrences. Full ordered assignments can be distinct even when a venue recurs across options. [Project source](../../lib/itinerary-pages.ts).

## Dependency

Reusable external software, declared in package.json or requirements.txt. A range is not an exact installed version. [Project source](../../package.json).

## Deployment

Installing/running a reviewed build on hosting infrastructure. Local startup and a frontend build are not deployment. [Project source](../../docs/task52-production-implementation-plan.md).

## Directed graph / edge

Nodes linked by directional relationships. An order edge before 1 after 2 means occurrence 1 must precede 2. [Project source](../../backend/journey.py).

## DOM — Document Object Model

The browser element tree React updates to present the interface. [Project source](../../app/page.tsx).

## DST — Daylight Saving Time

Seasonal local clock changes creating repeated/nonexistent times. Aware UTC arithmetic and conservative clock checks avoid guessing. [Project source](../../backend/feasibility.py).

## DTO — Data Transfer Object

A deliberately serializable record exchanged/stored across boundaries. Proposed cloud sessions need bounded versioned DTOs rather than live Python objects. [Project source](../../docs/task52-cloud-architecture-evaluation.md).

## Durable

Intended to survive process failure. Local signed synthetic crash tests do not establish power-loss or distributed durability. [Project source](../../docs/task52-q4c-offline-protocol-v1.md).

## Dwell

Time spent at a visit, distinct from travel. Exact/minimum/maximum/under/approximate have different bound semantics. [Project source](../../backend/advanced_timing.py).

## Ed25519

A public-key signature algorithm used in Q4C offline synthetic authority tests; it does not enroll real owner trust. [Project source](../../scripts/task52_q4c_auth.py).

## Egress / ingress

Traffic leaving/entering a service. Proposed public ingress and provider egress need independently reviewed security. [Project source](../../docs/task52-cloud-architecture-evaluation.md).

## Endpoint

Either an HTTP operation address or a journey final destination; context determines the meaning. An origin return endpoint is not a new activity. [Project source](../../backend/main.py).

## Environment variable

A named configuration value read by a process. Private database/provider values must not enter browser NEXT_PUBLIC variables. [Project source](../../next.config.ts).

## Evaluation corpus

A fixed collection of source scenarios and references for measuring extraction behavior. The 66-case corpus has uneven reference depth and pending independent review. [Project source](../../docs/task52-q1-qualification-v1.md).

## Exception

A failure signal that interrupts normal execution. Safe handlers translate exceptions without echoing private bodies. [Project source](../../backend/failures.py).

## Exclusive / inclusive

Exclusive under-5 excludes exactly 5; inclusive within-5 permits it. Comparisons must preserve source relation. [Project source](../../backend/location_policy.py).

## Fail closed

Refusing work when required safety evidence/state is missing or uncertain, rather than assuming permission. [Project source](../../backend/admission.py).

## FastAPI

The Python web framework registering routes and connecting Pydantic contracts to HTTP. [Project source](../../backend/main.py).

## Feasibility

Whether supplied evidence satisfies applicable requirements. Confirmed mock feasibility is not real-world availability. [Project source](../../backend/feasibility.py).

## Fence / fencing

A changing ownership/version marker proposed to prevent stale workers acting after a newer claim. Distributed authority remains future design. [Project source](../../docs/task52-admission-transport-v1.md).

## Field mask

A provider request list selecting response fields; selected fields affect returned facts and billing tier. [Project source](../../backend/search_fields.py).

## Filter

Remove candidates with disqualifying evidence. This is distinct from ranking remaining candidates. [Project source](../../backend/ranking.py).

## Fingerprint / HMAC

A keyed digest binding operation content without storing it as an ordinary log label. HMAC means Hash-based Message Authentication Code. [Project source](../../backend/admission.py).

## Fixture

Controlled invented or recorded input for reproducible tests. Fictional venues never prove live supply. [Project source](../../backend/real_fixtures.py).

## Foreign key / primary key

A primary key identifies a row; a foreign key links to a parent row, such as stop to itinerary. [Project source](../../backend/migrations/0001_initial_planning.sql).

## Frontend

The interface and browser-facing Next.js application, with components, state, clients and proxies. [Project source](../../app/page.tsx).

## Function

Named reusable logic receiving inputs and returning results or failures. [Project source](../../backend/planner.py).

## Geographic grounding

Checking provider components/coordinates against the supported requested destination/radius/exclusions, not inferring geography from a business name. [Project source](../../backend/venue_geography.py).

## Git / GitHub

Git records local version history; GitHub hosts the remote repository. Pushing uploads commits, not every untracked local file. [Project source](../../AGENTS.md).

## Gold reference

Expected interpretation used for evaluation. References can have gaps; independent adjudication is still needed. [Project source](../../docs/task52-q1-qualification-v1.md).

## Grounding

Supporting a claim with the correct source occurrence/meaning, not merely a plausible quote found elsewhere in the sentence. [Project source](../../backend/journey.py).

## HA — High Availability

Redundant hosting intended to tolerate failures. Proposed Redis HA is not durable financial authority. [Project source](../../docs/task52-cloud-architecture-evaluation.md).

## Hash / SHA-256

A one-way digest identifying bytes. It supports integrity binding but is not owner consent, a signature or semantic correctness. [Project source](../../backend/saved_plans.py).

## Hook

A React lifecycle/state function such as useEffect/useRef. Where To uses hooks in components rather than requiring a separate hooks directory. [Project source](../../app/page.tsx).

## HTTP / HTTPS

Hypertext Transfer Protocol transports requests/responses; HTTPS adds encrypted transport. Status codes need domain-code interpretation too. [Project source](../../app/api/interpret/route.ts).

## I/O — Input/output

Communication with files, networks or databases. Pure feasibility evaluation performs no provider I/O. [Project source](../../backend/feasibility.py).

## Idempotency

Repeating an equivalent operation avoids unintended duplicate effects. Saved fingerprints bind an existing selection rather than create arbitrary new rows. [Project source](../../backend/saved_plans.py).

## Immutability

Preserving a value rather than changing it in place. Frozen model outputs and historical journal rows must retain original bytes. [Project source](../../docs/task52-q1-qualification-v1.md).

## Inference

Running a trained model to generate output; not training, venue search or full itinerary generation. [Project source](../../backend/ai/ollama.py).

## Invariant

A condition that must remain true throughout work, such as required occurrence preservation and private origin exclusion. [Project source](../../backend/advanced_routing.py).

## Itinerary

An ordered proposed set of visits and connecting travel, with evidence/uncertainty rather than a booking. [Project source](../../backend/models.py).

## Journal

Durable attempt/financial/evidence records. Historical evaluation corrections append rather than overwrite prior failures. [Project source](../../docs/task52-q4b-journal-operator-review.md).

## JSON Schema

A machine-readable allowed-structure description derived from Interpretation and supplied to Ollama. It cannot prove source meaning. [Project source](../../backend/ai/ollama.py).

## JSON — JavaScript Object Notation

A structured text format with objects, arrays, strings, numbers, booleans and null; syntax validity is not semantic correctness. [Project source](../../backend/ai/__init__.py).

## JSX / TSX

Element-description syntax inside JavaScript/TypeScript; .tsx files define typed React components. [Project source](../../components/plan-card.tsx).

## Latency / p95

Time an operation takes; p95 is a named sample percentile. Model latency and full outing latency have different scopes. [Project source](../../docs/task52-ai-performance-evaluation.md).

## Lease

Temporary work ownership. Worker references can retain admission after the HTTP reader leaves. [Project source](../../backend/provider_work.py).

## Least privilege

Grant only needed powers. The saved-plan runtime role has bounded SELECT/INSERT with RLS, not administrator access. [Project source](../../backend/migrations/0002_private_saved_plans.sql).

## Lexicographic ranking

Compare ordered criteria in sequence, using later criteria only after earlier ties. Advanced routing uses this rather than ordinary weighted scoring. [Project source](../../backend/advanced_routing.py).

## LLM — Large language model

A trained token-sequence model, locally Qwen3 4B for extraction. It is not an authoritative database. [Project source](../../backend/ai/ollama.py).

## Load balancer

Proposed ingress service directing traffic among replicas; session/authorization state must remain shared correctly. [Project source](../../docs/task52-cloud-architecture-evaluation.md).

## Localhost / loopback

An address pointing to the same computer, such as 127.0.0.1. Current private/real development access is deliberately local. [Project source](../../lib/development-access.ts).

## Lock / race condition

A lock makes a critical section exclusive; a race is incorrect behavior due to overlapping state changes. A process lock alone does not coordinate a fleet. [Project source](../../backend/provider_budget.py).

## Matrix element

One origin-destination cell. A 3×4 matrix counts twelve elements even if sent in one request. [Project source](../../backend/routes_transport.py).

## Microdollar / nanodollar

One millionth / one billionth of a dollar, used for integer accounting at different boundaries. Always preserve the scale. [Project source](../../backend/development_cost.py).

## Middleware

A wrapper applying cross-cutting request rules such as body limits, admission and safe response headers. [Project source](../../backend/request_middleware.py).

## Migration

A versioned database schema change, not a study command to run against owner data. [Project source](../../backend/database_migrate.py).

## Mock

A replacement dependency/fixture. Mock Baltimore results are explicitly fictional and do not verify a real city. [Project source](../../backend/mock_data.py).

## Model

Context-dependent: trained AI, Pydantic data shape, or saved-document version. Do not assume changing one changes the others. [Project source](../../backend/models.py).

## Module / import

A file/unit providing names to other code; import makes its declarations available and may execute top-level code. [Project source](../../backend/main.py).

## Monotonic clock

A clock measuring elapsed intervals without calendar adjustments; current capability expiry uses it. It differs from destination date/route observation time. [Project source](../../backend/option_sessions.py).

## Next.js App Router

File-based pages and route handlers in app/. Consult the installed version-specific guides before code changes. [Project source](../../app/api/plans/generate/route.ts).

## Node.js

The JavaScript server runtime running Next.js and local launcher scripts. [Project source](../../scripts/dev-server.mjs).

## Nonce

A one-use identifier detecting replay in the signed offline Q4C protocol. It is not a substitute for trusted role authorization. [Project source](../../scripts/task52_q4c_protocol.py).

## Normalization

A controlled representation transformation. Legacy normalization can change graphs; preserve raw evidence and documented limits. [Project source](../../backend/journey.py).

## Null / None

Explicit missing/unknown data, distinct from zero or an empty known list. Unknown opening windows differ from known closure. [Project source](../../backend/models.py).

## OAuth

An authorization framework supplying short-lived access credentials to protected backend Google calls. This is not a browser API key. [Project source](../../backend/places_transport.py).

## Object / dictionary

Named fields grouped into one value, such as JSON text/preferences or Python status dictionaries. [Project source](../../backend/main.py).

## Observability

Bounded logs/metrics for understanding operations, deliberately excluding private content and credentials. [Project source](../../backend/operations.py).

## Occurrence

A specific source visit with its own index, even when another visit has the same category label. [Project source](../../backend/journey.py).

## Ollama

Local model-serving process exposing /api/chat on loopback by default. [Project source](../../backend/ai/ollama.py).

## Optionality

Whether a visit may be omitted. Whenever convenient changes ordering freedom; maybe coffee can mark optionality only with correct evidence. [Project source](../../backend/journey.py).

## Orchestrator

Logic coordinating state, providers and pure evaluators, such as real_plans or Session.run. [Project source](../../backend/advanced_planning.py).

## Origin

The explicitly confirmed start, separate from requested destination or unresolved home. Surprise Me has no private start leg. [Project source](../../components/location-controls.tsx).

## Partial order

Some required before/after relationships without a full sequence; coffee can float around pharmacy→bank. [Project source](../../backend/advanced_routing.py).

## Place ID

Google venue identity used for source references. It is not a capability authorizing arbitrary requests. [Project source](../../backend/venue_models.py).

## Pool / Cartesian product

A pool contains candidate venues; a product chooses one from each occurrence pool, potentially multiplying search size. [Project source](../../backend/planner.py).

## Port

A service number on a host: normal frontend 3000, backend 8000, Ollama 11434. [Project source](../../scripts/dev-server.mjs).

## PostgreSQL / psycopg

The relational database engine and Python driver used for private saved selections. [Project source](../../backend/saved_plans.py).

## PR — Pull request

A proposed branch change reviewed before merging. A push alone does not imply reviewed deployment. [Project source](../../AGENTS.md).

## Prompt

Model instructions/examples/source input. Few-shot examples guide inference without training weights. [Project source](../../backend/ai/ollama.py).

## Props / state

Props are component inputs; state is remembered interactive data updated through React. [Project source](../../app/page.tsx).

## Provenance

The source and ownership evidence for a claim, distinct from a provider name or a merely present quote. [Project source](../../backend/source_preparation.py).

## Provisional / unverified

A result with unresolved evidence rather than known complete confirmation. It is not permission to ignore hard constraints. [Project source](../../backend/ranking.py).

## Proxy

A server forwarding client requests to another service, with additional response/boundary checks. [Project source](../../app/api/plans/generate/route.ts).

## PTY — Pseudoterminal

A terminal simulation used in opt-in lifecycle tests; those tests must not stop unknown owner listeners. [Project source](../../backend/TESTING.md).

## Pure function

Logic evaluating supplied inputs without network/database effects; useful for reproducible evidence tests. [Project source](../../backend/feasibility.py).

## Pydantic

Python validation/schema library used for strict contracts and cross-field rules. [Project source](../../backend/models.py).

## Quota / rate limit

A quantity ceiling / interval-bound ceiling. They differ from warnings, billing alerts and per-user daily allowances (none introduced by Task 51). [Project source](../../backend/provider_budget.py).

## Qwen3 4B

Default local extraction model; four billion approximate parameters. Only Ollama is currently supported by the application factory. [Project source](../../backend/ai/__init__.py).

## Ranking

Ordering eligible options by declared preferences/evidence. It cannot override known infeasibility. [Project source](../../backend/ranking.py).

## React

Component/state library rendering the frontend interface. [Project source](../../app/page.tsx).

## Redis

Proposed volatile shared key-value store for temporary evidence/sessions, not current deployed infrastructure or sole spend authority. [Project source](../../docs/task52-cloud-architecture-evaluation.md).

## Regression

A previously working behavior broken by a change; relevant offline tests guard known invariants. [Project source](../../backend/TESTING.md).

## Regular expression

A bounded text-pattern language used for supported wording checks, not a general natural-language proof system. [Project source](../../backend/journey.py).

## Replica

One running service instance. Multiple replicas need shared sessions/admission and durable fences/reservations. [Project source](../../docs/task52-cloud-architecture-evaluation.md).

## Repository

The source/history collection, distinct from ignored private local data and external hosted state. [Project source](../../README.md).

## Reservation

Conservative accounting of intended attempts/exposure before dispatch. Failure does not imply an automatic refund or retry. [Project source](../../backend/development_cost.py).

## RLS — Row Level Security

PostgreSQL policies restrict which rows the runtime role can read/insert using access hash and expiry. [Project source](../../backend/migrations/0002_private_saved_plans.sql).

## Route handler

A Next.js route.ts function answering an HTTP method; FastAPI has its own separate endpoint functions. [Project source](../../app/api/interpret/route.ts).

## Runtime

The program executing code, such as browser JavaScript, Node.js or Python; source types alone do not execute. [Project source](../../package.json).

## Same origin

The same scheme, host and port. Protected local proxies compare the actual browser Origin/Host rather than assuming rewrites imply trust. [Project source](../../lib/persistence-proxy.ts).

## Schema

A declared structure/rule set, such as Pydantic fields or SQL table definitions. A schema match does not prove semantic correctness. [Project source](../../backend/models.py).

## SDK — Software Development Kit

A provider library. Hidden retries can violate attempt bounds; current transports explicitly disable HTTP retries. [Project source](../../backend/routes_transport.py).

## Serialization

Converting values into transferable/storage form. Public model dumping must exclude private origin data; repr hiding alone is insufficient. [Project source](../../backend/real_planning.py).

## Session

Context-dependent remembered state: browser submission, backend outing, SQL connection or proposed cloud identity. Name the scope when debugging. [Project source](../../backend/option_sessions.py).

## Signature

Cryptographic authentication of exact bytes under a pinned trusted public key. It does not itself prove human independence or grant another purpose. [Project source](../../scripts/task52_q4c_auth.py).

## Source compatibility

Binding evidence to exact code/schema/prompt/scorer identities so changed runtime behavior is not mislabeled historical execution. [Project source](../../docs/task52-source-compatibility-v1.md).

## Source-owned occurrence

A specific visit tied to one position in the original words. In “Tea, museum, tea,” each tea visit has its own source span and index. The V5.1 development adapter requires the same visit to retain its source span and index through legacy validation before preserving its edges. [Validation chapter](09-validation-source-grounding-and-ordering-rules.md)

## SQL — Structured Query Language

Database read/write/schema language; psycopg uses parameter binding rather than interpolating untrusted SQL values. [Project source](../../backend/saved_plans.py).

## SQLite

A local file database used in offline evaluation protocols, distinct from production saved-plan PostgreSQL. [Project source](../../scripts/task52_q4c_protocol.py).

## Staging area

The Git index selecting what enters the next commit. Explicit paths prevent accidental inclusion of unrelated owner work. [Project source](../../AGENTS.md).

## Structured output

A model response constrained to a schema, still requiring strict decoding and source/semantic validation. [Project source](../../backend/ai/ollama.py).

## Supabase

The hosted PostgreSQL platform used for private saved plans via restricted backend SQL, not a public browser data client. [Project source](../../docs/database-setup.md).

## Tailwind

CSS utility tooling used alongside globals.css; styling does not own planning semantics. [Project source](../../package.json).

## Test clock

Explicit fixture-controlled time scoped to a test and restored afterward. Calendar fixtures do not freeze monotonic or route clocks. [Project source](../../backend/testing_clock.py).

## Timeout

A bound on waiting. An expired/canceled client wait does not prove no provider request was sent. [Project source](../../backend/provider_work.py).

## TLS — Transport Layer Security

Encrypted transport required by the runtime PostgreSQL connection; HTTPS uses TLS for web traffic. [Project source](../../backend/saved_plans.py).

## Token

A text-processing chunk for AI, an OAuth credential, or a scoped capability depending on context. Never treat them as interchangeable. [Project source](../../backend/ai/__init__.py).

## Topology

The actual leg structure: optional origin→first, inter-activity links and final return/destination. [Project source](../../backend/advanced_routing.py).

## Transaction

An atomic unit of database work, committing all related writes or rolling them back. It cannot unsend external HTTP. [Project source](../../backend/saved_plans.py).

## Transitive closure

All dependencies implied through paths: A→B and B→C imply A precedes C even if B is an omitted optional visit. [Project source](../../backend/advanced_routing.py).

## Trust boundary

Where less-trusted data is checked before gaining authority, such as strict extraction before planning handoff. [Project source](../../backend/interpretation.py).

## TTL — Time to live

A state retention/admission lifetime, such as a 600-second continuation; capacity eviction can remove it earlier. [Project source](../../backend/option_sessions.py).

## TypeScript

JavaScript with development-time types; actual HTTP JSON still needs runtime checks. [Project source](../../lib/planning-client.ts).

## Untracked

A working file absent from Git tracked history, not permission to delete or stage it incidentally. V5 research pre-existed this task and was independently committed during authoring. [Project source](../../AGENTS.md).

## URL — Uniform Resource Locator

A resource address with scheme/host/port/path, such as the local health endpoint. Private capabilities must not leak into logs. [Project source](../../app/api/health/route.ts).

## UTC — Coordinated Universal Time

A common instant reference for elapsed calculations; destination-local clocks still need timezone conversion. [Project source](../../backend/advanced_timing.py).

## Uvicorn

The server process running FastAPI; the launcher controls its local lifecycle. [Project source](../../backend/dev_start.py).

## Validation

Checking shape and applicable rules; normalization transforms representation. Neither proves arbitrary-language completeness. [Project source](../../backend/interpretation.py).

## Verification

Evidence from a specified check. Source, offline tests, browser interaction, live calls and independent qualification are different claims. [Project source](../../HANDOVER.md).

## Virtual environment

An isolated Python dependency installation, here backend/.venv, distinct from a separate Git checkout. [Project source](../../backend/TESTING.md).

## Weighted score

A sum of normalized evidence components with declared weights; real scoring uses quality/convenience rather than invented affordability. [Project source](../../backend/ranking.py).

## Worktree

A separate checkout sharing Git history, useful for isolated later learning edits without mixing current dirty files. [Project source](../../AGENTS.md).

## XSS — Cross-Site Scripting

Malicious script execution in a page, which can threaten bearer capabilities; random tokens do not make theft harmless. [Project source](../../docs/database-security.md).

## Issued pending snapshot (local experiment)

An existing pending DTO whose exact typed content and raw-evidence identity are remembered by the disposable V5.1 fixture until its original deadline. It is checked before renewed source proof, never accepted as a credential or raw AI output. [Implementation](../../scripts/task52_v51_local_continuation.py).

**Standalone output:** Next.js server bundle and traced runtime dependencies emitted by `output: "standalone"`; static files must also be packaged. **Image digest:** SHA256 identity of a container image/index; pinning it fixes a build input, not application qualification. **Build context:** Files Docker can read during a build; this repository uses a default-deny `.dockerignore`. **Workload identity:** Service-owned cloud authentication, distinct from copying a developer credential into a container; required hosted adapters remain unimplemented.

**Colima profile:** A named local Linux VM/runtime configuration; `whereto-task52` is isolated from the default Docker context. **Rosetta Linux emulation:** Apple’s translation support used here to execute amd64 application containers in an arm64 VM; it does not change the reviewed target dependencies. **Vulnerability match:** A scanner’s package/advisory association, distinct from proven exploitability; severity and fix status require contextual review.

**Advisory-database drift:** Changed scanner results caused by new advisory data rather than changed image packages. Compare the same original image and the patched image using one database identity. **Deployment-only security override:** A single explicitly reviewed dependency version in the deployment lock that differs from historical/local evidence; it is not a new paid-evaluation approval.

## Shared-authority reference terms

- **Fencing number**: a monotonically increasing ownership number; an older worker cannot commit under a newer claim.
- **Uncertain operation**: an admitted operation whose external result is unknown; retain exposure and do not resend automatically.
- **UNLOGGED table**: PostgreSQL data without normal crash-recovery logging; the prototype uses it only for disposable fictional evidence. It is not an approved real private-data store.

See [shared-state limits](../../docs/task52-shared-state-foundations.md).
