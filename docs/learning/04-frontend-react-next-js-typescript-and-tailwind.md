# 04 — Frontend React Next.js TypeScript and Tailwind

[Course contents](README.md) · [Glossary](GLOSSARY.md)

## Build the interface from components

A **component** is a reusable interface function. React calls components to describe what should appear; the browser updates its **DOM**, Document Object Model, the tree of elements on the page. Where To? needs reusable components because ordinary, advanced and saved plans share card and detail presentation.

[app/page.tsx](../../app/page.tsx) is the main interactive page. [components/plan-card.tsx](../../components/plan-card.tsx) renders a plan; [location-controls.tsx](../../components/location-controls.tsx) manages origin selection; [outing-date-field.tsx](../../components/outing-date-field.tsx) keeps date entry consistent. `tsx` means TypeScript with JSX (JavaScript XML), a syntax for writing element descriptions inside code. **Props** are inputs passed to a component, such as a plan or callback.

**State** is a value React remembers between renders. Changing it requests another render. A **hook** is a React function such as `useEffect` or `useRef` for managing component lifecycle and retained values. A ref can retain a mutable controller or page collection without itself requesting rendering. The project keeps orchestration in the main page and reusable helpers in `lib/`; there is no need to invent a separate `hooks/` directory to explain it.

## A real effect, line by line

This is the existing page's planning-mode effect, reformatted for reading:

```typescript
useEffect(() => {
  let active = true;
  void fetch("/api/planning-mode", { cache: "no-store", signal: AbortSignal.timeout(5000) })
    .then(r => r.json())
    .then(value => { if (active && value.enabled && ["real", "mock"].includes(value.mode)) {
      setDataMode(value.mode); setLookupEnabled(value.startingLookupEnabled === true);
    } }).catch(() => {});
  return () => { active = false; };
}, []);
```

Line 1 registers work after mounting. Line 2 tracks whether this instance still owns the result. Line 3 requests mode metadata with a five-second bound; `void` explicitly discards the promise as a return value. Line 4 decodes JSON. Lines 5–6 accept known enabled modes and update state. Line 7 absorbs failure so the existing safe interface can remain usable. Line 8 is cleanup: late replies must not change an unmounted page. Line 9's empty dependency list means the effect is tied to mounting rather than every render. Its input is backend mode metadata; its output is state updates. It does not request GPS, venues or an itinerary.

A **promise** represents an eventual result or failure. `.then` and `await` are two ways to handle it. A **callback** is a function passed to another operation; `onInterpreted` and `onClarification` in `runPlanning` connect client results to the form.

## Events connect buttons to planning

`submit` prevents the browser's default form navigation and calls `runPlanning`. `runPlanning` starts a controller through [PlanningSession](../../lib/planning-session.ts), clears stale pages and detail state, calls `generateOuting`, and checks ownership before updating results. `showDifferent` and `answerAdvanced` handle continuation. Source inspection confirms those connections; it is not a fresh browser test.

TypeScript's `type` declarations describe accepted shapes. For example [lib/advanced-planning.ts](../../lib/advanced-planning.ts) describes an `AdvancedOption`, then `adaptAdvanced` checks actual runtime data. Types help developers catch mistakes before execution, but network JSON arrives at runtime and needs checks too. A **union** such as `'driving' | 'walking'` permits either exact value, not arbitrary text. `string | null` permits a string or an explicitly missing value.

## Next.js and styling

Next.js uses the **App Router**, where files under `app/` define pages and route handlers. [layout.tsx](../../app/layout.tsx) wraps pages; `page.tsx` defines a page; `route.ts` defines HTTP handling. Consult the installed Next.js guide at `node_modules/next/dist/docs/01-app/03-api-reference/03-file-conventions/route.md`, because this repository explicitly warns against relying on older conventions.

**CSS**, Cascading Style Sheets, controls appearance. Tailwind supplies composable utility classes; [globals.css](../../app/globals.css) also contains the project's actual styling. [package.json](../../package.json) declares Next `^16.0.0`, React `^19.0.0`, TypeScript `^5.0.0` and Tailwind `^4.0.0`. A caret is a permitted version range, not the exact installed version; the lockfile records resolved packages. Preserve the existing design when learning behavior.

If rendering fails, inspect the first console error and relevant adapter/component. Do not bypass runtime response validation to make broken cards appear. Chapter 15 shows how to separate an interface failure from an unavailable backend.

## Five key takeaways

1. Components describe interface structure.
2. Props are inputs; state is remembered interactive data.
3. Effects need cleanup for late results.
4. TypeScript types do not validate arbitrary JSON.
5. Styling and planning authority live in different places.

## Check your understanding

04.Q1. What is a prop?
04.Q2. Why is active set false during cleanup?
04.Q3. Does the mount effect plan an outing?
04.Q4. What does a TypeScript union mean?
04.Q5. Where do HTTP route handlers live?

## Code-reading exercise — 04.R

Locate submit, runPlanning, showDifferent and answerAdvanced in app/page.tsx. Write which user action each serves.

## Practical exercise — 04.P

Use rg -n "useEffect|runPlanning|async function submit" app/page.tsx; inspect the lines without changing CSS.

See [separate answers and guidance](EXERCISE_SOLUTIONS.md#chapter-04).

[Previous chapter](03-overall-application-architecture.md) · [Contents](README.md) · [Next chapter](05-backend-python-fastapi-and-pydantic.md)


## Inactive ordinary private browser checkpoint

`PrivateOrdinaryExperience` reuses existing styles, artwork, date/summary/card components. `PrivateOrdinaryClient` uses ordinary React-owned memory, not browser storage. Separate interpretation, pending-answer and confirmation/generation buttons prevent automatic repeated work. Native fetch is invoked through a closure rather than as a controller method; a real-browser finding and regression test cover that binding. See the [UI/recovery report](../task52-ordinary-private-ui.md).


### Private frontend server network channel

`lib/server-https.ts` adds `createHTTPSChannel({audience, endpoint})`. A server-owned enrollment maps the exact intended backend audience to an HTTPS service origin. The existing identity port supplies verified user/workload proofs; browser headers never supply trusted service credentials. Request bytes are preserved, only five ordinary paths are allowed, redirects/retries are refused and cancellation closes the socket. The image contains a closed constructor; the more general test Agent constructor and synthetic preload are not exported in the shipped artifact.

The existing UI is unchanged. Actual standalone-container tests cover pending date, confirmed coordinates, ordinary cards, local details and discard. Mobile390px and desktop1280px layouts were visually checked. Advanced/discovery/persistence remain blocked. The local fake IdP has its own test-only process/key; the frontend receives neither that signing key nor a Docker/controller credential. [Report](../task52-production-service-packaging.md).


### Task 52 closed frontend and immutable recovery checks

`lib/private-frontend-startup.ts` composes the existing ordinary server profile once. It waits for trusted identity initialization and a certificate-verified backend connection, then installs the existing handler. Failed initialization closes resources and cannot fall back to anonymous/local-model behavior. This is compiled only into the separate private image; normal Next startup does not import it. The sealed configuration contains endpoints and a frontend proof key, never client-selected extraction or financial authority. See [verification report](../task52-closed-frontend-verification.md).
