# Learning exercise workbook

There are **140 activities**: five comprehension questions, one source-reading exercise and one practical exercise per chapter. All exercises can be answered without AI inference, Google requests, hosted database operations or cloud resources. [Separate solutions](EXERCISE_SOLUTIONS.md).

## Safety and progression

Chapters 1–6 are read-only source/navigation work. Chapters 7–14 use paper traces, fictional calculations and code reading. Chapters 15–20 introduce optional offline verification and patch proposals. No exercise asks you to modify production behavior, alter a prompt/policy, clear a halt, reset accounting or change approvals.

Run read-only commands from `/Users/rahularutla/Documents/whereto`. Never paste `.env` files, saved links, full Network payloads, credentials or private journal contents into notes/screenshots/shared chats.

## Optional separate environment for later coding practice

A branch alone shares dirty working files. For optional later experiments, first inspect status and choose a reviewed commit. The following creates a **separate** local checkout and branch; it mutates Git metadata, so understand it before using it. Do not run it if that folder/branch already exists. It is not needed to read the course.

```sh
cd /Users/rahularutla/Documents/whereto
git status --short
git worktree add -b codex/learning-practice /private/tmp/whereto-learning-practice HEAD
cd /private/tmp/whereto-learning-practice
pwd
git status --short
```

Use the committed handbook baseline you reviewed; `HEAD` means the commit selected when you run the command. Do not copy private local profiles or credentials. Do not start real-mode services or run cloud evaluator scripts there. Dependency installation can access package registries and is a separate setup step; review package scripts/configuration first. For dependency-free practice, write a small scratch calculation using invented values, or make a prose-only explanation patch. A production behavior change is not required by any exercise.

Do not use `git reset --hard`, `git clean`, `rm -rf`, force-push or automatic worktree removal. Leave experiment files until you have reviewed what is disposable. The course author did not create a worktree or application patch merely to demonstrate this procedure.

## All activities

## Chapter 01: What Where To Does and Everything Built So Far

[Read chapter](01-what-where-to-does-and-everything-built-so-far.md)

- **01.Q1:** What does an itinerary contain?
- **01.Q2:** Why can a healthy backend still fail to plan?
- **01.Q3:** Can the mock catalog prove a Sydney plan exists?
- **01.Q4:** Is an offline ordering policy active production enforcement?
- **01.Q5:** Which task remains outside this work?
- **01.R — Code reading:** Open backend/main.py and locate health and generate_plan. List two dependencies used only by planning.
- **01.P — Practical:** Run pwd, git status --short, and git log -3 --oneline from the repository. Do not edit anything.

## Chapter 02: Programming and Web Development Fundamentals

[Read chapter](02-programming-and-web-development-fundamentals.md)

- **02.Q1:** How does None differ from zero here?
- **02.Q2:** What executes TypeScript after transformation?
- **02.Q3:** What does a port identify?
- **02.Q4:** Does async mean unlimited parallel work?
- **02.Q5:** What is a dependency?
- **02.R — Code reading:** Read supports_location and _pools in backend/planner.py. Find where a false coverage result becomes a PlanningError.
- **02.P — Practical:** Use rg -n "def supports_location|unsupported_location" backend/planner.py. Explain the two matches aloud.

## Chapter 03: Overall Application Architecture

[Read chapter](03-overall-application-architecture.md)

- **03.Q1:** Which layer renders cards?
- **03.Q2:** Which layer validates model output?
- **03.Q3:** What is a trust boundary?
- **03.Q4:** Does a proxy make browser payloads trustworthy?
- **03.Q5:** Why does production startup refuse?
- **03.R — Code reading:** Read app/api/plans/generate/route.ts and backend/main.py. Find the two functions that receive the same path at different layers.
- **03.P — Practical:** Draw the architecture on paper and mark each component as browser, local service, external service or proposed.

## Chapter 04: Frontend React Next.js TypeScript and Tailwind

[Read chapter](04-frontend-react-next-js-typescript-and-tailwind.md)

- **04.Q1:** What is a prop?
- **04.Q2:** Why is active set false during cleanup?
- **04.Q3:** Does the mount effect plan an outing?
- **04.Q4:** What does a TypeScript union mean?
- **04.Q5:** Where do HTTP route handlers live?
- **04.R — Code reading:** Locate submit, runPlanning, showDifferent and answerAdvanced in app/page.tsx. Write which user action each serves.
- **04.P — Practical:** Use rg -n "useEffect|runPlanning|async function submit" app/page.tsx; inspect the lines without changing CSS.

## Chapter 05: Backend Python FastAPI and Pydantic

[Read chapter](05-backend-python-fastapi-and-pydantic.md)

- **05.Q1:** Why inherit OutingRequest?
- **05.Q2:** What does Field(...) mean?
- **05.Q3:** Can 32 extracted stops all execute?
- **05.Q4:** Does repr=False remove a JSON field?
- **05.Q5:** What status represents invalid structured request input?
- **05.R — Code reading:** Compare OutingRequest, PlanningRequest and PlannerInput. Identify one field or rule added at each level.
- **05.P — Practical:** Use rg -n "class (OutingRequest|PlanningRequest|PlannerInput)" backend/models.py backend/real_planning.py. Do not submit a request.

## Chapter 06: APIs HTTP JSON and Frontend Backend Communication

[Read chapter](06-apis-http-json-and-frontend-backend-communication.md)

- **06.Q1:** What does Content-Type describe?
- **06.Q2:** Why call JSON.stringify?
- **06.Q3:** Can a 200 reply contain no plan?
- **06.Q4:** Which variable selects the proxy backend?
- **06.Q5:** Is a failed network response proof nothing was billed?
- **06.R — Code reading:** Read both interpret route handlers and find where malformed JSON, invalid shape and unavailable AI receive different treatment.
- **06.P — Practical:** Write a JSON interpretation body in a scratch note, then identify each property in InterpretationInput without sending it.

## Chapter 07: Complete End to End Outing Request Lifecycle

[Read chapter](07-complete-end-to-end-outing-request-lifecycle.md)

- **07.Q1:** Why can A fail in mock mode?
- **07.Q2:** What is not established by a cinema venue?
- **07.Q3:** Which edge does frozen V4 prove for C?
- **07.Q4:** Is coffee optional in D?
- **07.Q5:** Why does Surprise Me stop E?
- **07.R — Code reading:** Follow requireOrigin from lib/planning-client.ts into components/location-controls.tsx, then find the backend no-origin return guard.
- **07.P — Practical:** For A–E draw a branch diagram and put a question mark at every fact the original sentence does not supply. Do not submit the examples.

## Chapter 08: AI Interpretation Qwen Ollama Prompts and Structured JSON

[Read chapter](08-ai-interpretation-qwen-ollama-prompts-and-structured-json.md)

- **08.Q1:** What does inference mean?
- **08.Q2:** Are prompt examples training?
- **08.Q3:** What is num_predict bounding?
- **08.Q4:** Why is JSON Schema insufficient?
- **08.Q5:** Can clarification avoid another model call?
- **08.R — Code reading:** Read AISettings.from_env and OllamaProvider._interpret. Identify provider URL, model, schema and output bound.
- **08.P — Practical:** Run rg -n "model:|base_url:|timeout_seconds:|num_predict" backend/ai/__init__.py backend/ai/ollama.py. Do not run a smoke or benchmark script.

## Chapter 09: Validation Source Grounding and Ordering Rules

[Read chapter](09-validation-source-grounding-and-ordering-rules.md)

- **09.Q1:** What is provenance?
- **09.Q2:** Why are two coffee stops not one node?
- **09.Q3:** Can an acyclic edge be wrong?
- **09.Q4:** Does the V4 observer enforce its decision?
- **09.Q5:** Why version V5 expectations?
- **09.R — Code reading:** Read the forward-edge removal condition in validate_journey. Compare it to the later edge cue test.
- **09.P — Practical:** Write the node/edge tables for “coffee, museum, then coffee” under frozen V4 and proposed V5, clearly labeling both policies.

## Chapter 10: Planning Algorithms Filtering Scheduling and Ranking

[Read chapter](10-planning-algorithms-filtering-scheduling-and-ranking.md)

- **10.Q1:** How many products have pools of size 2 and 3?
- **10.Q2:** Why is a straight-line gap not travel evidence?
- **10.Q3:** Can a rating override a known hard violation?
- **10.Q4:** What does unknown upper dwell imply for a whole-trip maximum?
- **10.Q5:** Why is no result not proof of city-wide impossibility?
- **10.R — Code reading:** Read score_candidates and AdvancedRouter._shortlist. Find one ranking formula and one branch limiting visit permutations.
- **10.P — Practical:** Using the fictional dinner/drinks timeline, move the end to 19:30, then change the travel cap to under 12 minutes. Explain each result without running providers.

## Chapter 11: Google Places and Routes APIs

[Read chapter](11-google-places-and-routes-apis.md)

- **11.Q1:** How many elements are 3 origins by 4 destinations?
- **11.Q2:** What does a field mask select?
- **11.Q3:** Why is A→B not enough for a return?
- **11.Q4:** What does ADC mean?
- **11.Q5:** When does current route evidence expire?
- **11.R — Code reading:** Read routes_transport.compute_matrix and find authentication, accounting, HTTP send and error handling in order.
- **11.P — Practical:** Draw a fictional two-by-two matrix and count all cells including diagonals. Use no Maps requests.

## Chapter 12: PostgreSQL Supabase Sessions and Saved Plans

[Read chapter](12-postgresql-supabase-sessions-and-saved-plans.md)

- **12.Q1:** What connects stops to itineraries?
- **12.Q2:** What does rollback do?
- **12.Q3:** Are raw saved access tokens stored in SQL?
- **12.Q4:** Does forgetting a link revoke shared copies?
- **12.Q5:** Do saved real plans retain fresh route metrics?
- **12.R — Code reading:** Read database, write_document and read_document in saved_plans.py, then locate the matching RLS policy.
- **12.P — Practical:** Draw one plan with two option rows and their stops. Mark which rows must commit together; do not connect to Supabase.

## Chapter 13: State Management Caching and Request Lifecycles

[Read chapter](13-state-management-caching-and-request-lifecycles.md)

- **13.Q1:** What prevents a second page submission?
- **13.Q2:** Does Previous perform a Places search?
- **13.Q3:** Can a 10-minute token certify a 9-minute-old route?
- **13.Q4:** What survives a backend restart?
- **13.Q5:** Does session eviction mean the outing date expired?
- **13.R — Code reading:** Read PlanningSession.cancel, ItineraryPages.navigate and OptionSessions.get. Compare their failure behavior.
- **13.P — Practical:** Draw three independent timelines: selected calendar date, 600-second session, 300-second route evidence. Mark where a continuation can fail.

## Chapter 14: Security Rate Limits Accounting and Reliability

[Read chapter](14-security-rate-limits-accounting-and-reliability.md)

- **14.Q1:** What is middleware?
- **14.Q2:** Why keep a worker lease after browser cancellation?
- **14.Q3:** Are cost alerts hard spending stops?
- **14.Q4:** Can a saved token certify a new ordering graph?
- **14.Q5:** Why avoid raw request text in logs?
- **14.R — Code reading:** Read RequestManagement and provider_work.run_work. Find where HTTP ownership and worker ownership differ.
- **14.P — Practical:** Draw a duplicate-click race and insert the active fingerprint lock. Use fictional requests and do not modify real quotas.

## Chapter 15: Testing Mocks Debugging and Error Handling

[Read chapter](15-testing-mocks-debugging-and-error-handling.md)

- **15.Q1:** What is a fixture?
- **15.Q2:** What does an assertion do?
- **15.Q3:** Why not move every expired fixture date forward?
- **15.Q4:** Does a build prove planning behavior?
- **15.Q5:** Can sanitized aggregate logs recover every original response?
- **15.R — Code reading:** Read one test in test_hitec_geography.py and identify invented inputs, replaced dependencies and the assertion.
- **15.P — Practical:** After inspecting backend/TESTING.md, run only backend/.venv/bin/python -m unittest backend.test_planner -v in a disposable learning checkout if desired. Record actual output, not expected totals.

## Chapter 16: Git GitHub and the Development Workflow

[Read chapter](16-git-github-and-the-development-workflow.md)

- **16.Q1:** What does HEAD identify?
- **16.Q2:** Does git diff show untracked contents?
- **16.Q3:** What does push do?
- **16.Q4:** Why avoid git add . here?
- **16.Q5:** Why use a separate worktree for lessons?
- **16.R — Code reading:** Run git log -3 --oneline -- backend/journey.py and compare one commit message with the corresponding diff.
- **16.P — Practical:** Write a staging plan naming only docs/learning and README/HANDOVER. Explain why scripts/task52_ordering_v5.py is excluded.

## Chapter 17: Task 52B Cloud AI Evaluation and Ordering Research

[Read chapter](17-task-52b-cloud-ai-evaluation-and-ordering-research.md)

- **17.Q1:** How many original slots were proposed?
- **17.Q2:** Why keep a failed row after a decoder correction?
- **17.Q3:** What is the difference between raw correctness and safe blocking?
- **17.Q4:** Does a hash authorize paid work?
- **17.Q5:** Why is no cloud model qualified?
- **17.R — Code reading:** Compare the Q1 three outcome axes with the V4 policy and locate execution_authorized in task52_q4c_auth.py.
- **17.P — Practical:** Create a paper comparison with columns original source, immutable raw output, old rubric result and proposed V5 result. Use invented examples only; edit no frozen artifact.

## Chapter 18: Cloud Hosting Deployment and Scalability

[Read chapter](18-cloud-hosting-deployment-and-scalability.md)

- **18.Q1:** What is a replica?
- **18.Q2:** Why is Redis alone insufficient for spending authority?
- **18.Q3:** What does HA stand for?
- **18.Q4:** Does a frontend build activate the backend?
- **18.Q5:** What does p95 describe?
- **18.R — Code reading:** Read validate_environment and the proposal shared-session contract. Find one state currently tied to monotonic process time that needs a shared representation.
- **18.P — Practical:** On paper route a continuation to a second replica. List the state it would need and which proposed store owns each item.

## Chapter 19: How to Read Debug and Modify This Codebase Yourself

[Read chapter](19-how-to-read-debug-and-modify-this-codebase-yourself.md)

- **19.Q1:** What is an invariant?
- **19.Q2:** Why search literal error wording?
- **19.Q3:** What makes a reproduction minimal?
- **19.Q4:** Should a missing route become a guessed distance?
- **19.Q5:** Which evidence helps a focused help request?
- **19.R — Code reading:** Find the Surprise Me notice and follow requireOrigin back to generateOuting. Then locate the backend return-origin refusal.
- **19.P — Practical:** Write a hypothetical patch proposal to improve an error explanation. Specify affected file, acceptance criteria and one existing check; do not apply it.

## Chapter 20: Complete Project Glossary and Technical Reference

[Read chapter](20-complete-project-glossary-and-technical-reference.md)

- **20.Q1:** Name two meanings of model.
- **20.Q2:** Does verified identity verify price?
- **20.Q3:** Is a hash equivalent to a signature?
- **20.Q4:** What does 1020 represent in ordinary schedules?
- **20.Q5:** What should happen to old outputs after a policy change?
- **20.R — Code reading:** Compare DataQuality fields with the real Venue construction in real_planning.py. Identify which values remain unknown.
- **20.P — Practical:** Choose ten glossary terms and explain each using a different repository file. Check your explanations against the reference.
