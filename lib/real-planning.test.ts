import assert from "node:assert/strict";
import test from "node:test";
import { spawn } from "node:child_process";
import { createServer } from "node:http";
import { once } from "node:events";
import { generateOuting, adaptRanking, type ValidatedOuting } from "./planning-client";
import { EMPTY_PREFERENCES } from "./planner";
import { POST as interpret } from "../app/api/interpret/route";
import { POST as plan } from "../app/api/plans/generate/route";
import { POST as details } from "../app/api/venues/details/route";
import { POST as options } from "../app/api/plans/options/route";
import { POST as startingAreas } from "../app/api/starting-areas/route";
import { FirstPreference } from "./first-preference";
import { StartingAreaSession } from "./starting-areas";
import { POST as startingPlaces } from "../app/api/starting-places/route";
import { GET as mode } from "../app/api/planning-mode/route";
import { VenueDetailsSession, safeWebsite } from "./venue-details";
import { StartingConfirmation } from "./starting-confirmation";
import { StartingPlaceSession } from "./starting-places";
import { expandedOptions, nextOptions } from "./option-batches";

test("offline real mode: AI → HTTP backend → Google fixtures → existing planner → proxies/cards/contact details", async () => {
  const listener = createServer(); listener.listen(0, "127.0.0.1"); await once(listener, "listening");
  const addr = listener.address(); assert.ok(addr && typeof addr === "object");
  await new Promise<void>(r => listener.close(() => r()));
  const previous = process.env.BACKEND_URL;
  const base = `http://127.0.0.1:${addr.port}`;
  process.env.BACKEND_URL = base;
  const backend = spawn("backend/.venv/bin/python", ["-m", "backend.real_fixture_server", "--port", String(addr.port), "--reference-time", "2026-11-05T15:00:00+00:00"]);
  let mockMode=false;
  const send: typeof fetch = async (path, init) => {
    if(path==="/api/plans/generate" && init?.body){const body=JSON.parse(init.body as string);if(!body.startingLocation&&body.planningMode!=="surprise")body.startingLocation=mockMode?{point:{id:"Mock_origin_0",coordinates:{latitude:0,longitude:0}},source:"mock",explicitly_authorized:true}:{point:{id:"authorized-start",place_id:"Fixture_origin_0"},explicitly_authorized:true,source:"manual"};init={...init,body:JSON.stringify(body)};}
    const request = new Request(`http://localhost${path}`, init);
    return path === "/api/starting-areas" ? startingAreas(request) : path === "/api/starting-places" ? startingPlaces(request) : path === "/api/plans/options" ? options(request) : path === "/api/interpret" ? interpret(request) : path === "/api/venues/details" ? details(request) : plan(request);
  };
  const scenario = (name: string) => {mockMode=name==="mock";return fetch(`${base}/__test/scenario`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name }) });};
  try {
    for (let i = 0; i < 600; i++) {
      try { if ((await fetch(`${base}/health`)).ok) break; } catch { /* local startup */ }
      await new Promise(r => setTimeout(r, 50));
    }
    assert.equal((await (await mode()).json()).mode, "real");
    let asked = false;
    const result = await generateOuting("Plan bowling followed by dinner in Baltimore on Saturday, November 7, 2026, for 4 people.", EMPTY_PREFERENCES, { onClarification: value => { asked = !!value?.questions.length; } }, send);
    assert.equal(asked, false);
    assert.equal(result.plans[0].date, "2026-11-07");
    assert.equal(result.plans[0].people, undefined);
    assert.equal(result.dataMode, "real");
    assert.equal(result.plans.length, 3);
    assert.deepEqual(result.plans[0].venues.map(v => v.activity), ["bowling", "food"]);
    assert.ok(result.plans.every(p => p.price === null && p.feasibility === "provisional"));
    assert.ok(result.plans.every(p => !p.title.includes("Real outing option") && p.title.includes(p.venues[0].name)));
    assert.match(result.plans[0].description, /minutes driving between stops/);
    assert.ok(result.plans[0].venues.some(v=>v.rating!=null && (v.ratingCount??0)>0));
    assert.equal(result.plans[0].label, "OPTION 1 · BOWLING + DINNER");
    assert.equal(result.plans[0].title, result.plans[0].venues.map(v => v.name).join(" & "));
    const countsBefore = await (await fetch(`${base}/__test/counts`)).json();
    const second = adaptRanking(await (await send("/api/plans/options", {method:"POST",body:JSON.stringify({token:result.optionsToken})})).json());
    const third = adaptRanking(await (await send("/api/plans/options", {method:"POST",body:JSON.stringify({token:result.optionsToken})})).json());
    assert.equal(result.alternativeBatches?.length, 0);
    assert.equal(third.alternativeBatches?.length, 0);
    assert.equal(nextOptions(third), third);
    const all = [...result.plans, ...second.plans, ...third.plans];
    assert.equal(new Set(all.map(p => p.venues.map(v => v.id).join("/"))).size, 9);
    assert.ok(all.every(p => p.date === "2026-11-07" && p.people === undefined));
    const afterAlternatives=await (await fetch(`${base}/__test/counts`)).json();
    assert.equal(afterAlternatives.searches,countsBefore.searches);
    assert.equal(afterAlternatives.details,0);
    assert.ok(afterAlternatives.elements>=countsBefore.elements&&afterAlternatives.elements<=150);
    assert.equal(countsBefore.elements, 42);
    assert.equal(new Set(result.plans.map(p => p.venues[0].id)).size, 3);
    let expanded = result;
    const ids = new Set(all.map(p => p.id));
    for (let i = 0; i < 14; i++) {
      const response = await send("/api/plans/options", { method: "POST", body: JSON.stringify({ token: result.optionsToken }) });
      assert.ok(response.ok);
      expanded = adaptRanking(await response.json());
      for (const p of [...expanded.plans, ...(expanded.alternativeBatches ?? []).flat()]) { assert.ok(!ids.has(p.id)); ids.add(p.id); }
      if ((await (await fetch(`${base}/__test/counts`)).json()).elements >= 100) break;
    }
    assert.ok(ids.size > 9);
    assert.equal((await (await fetch(`${base}/__test/counts`)).json()).searches, 2);
    const manual = await generateOuting("Bowling then dinner in Baltimore for 2 people on 2026-11-07", EMPTY_PREFERENCES, { locationContext: { manualStartingPlace: "Inner Harbor, Baltimore" } }, send);
    assert.equal(manual.plans.length, 0);
    assert.match(manual.message, /Find and confirm/);
    assert.equal(manual.message.match(/Find and confirm/g)?.length, 1);
    const countsAfter = await (await fetch(`${base}/__test/counts`)).json();
    assert.equal(countsAfter.searches, countsBefore.searches);
    assert.equal(countsAfter.elements, 106);
    assert.equal((await (await fetch(`${base}/__test/counts`)).json()).details, 0);
    const p = result.plans[0], venue = p.venues[0];
    assert.equal(venue.id, venue.providerPlaceId);
    const contacts = new VenueDetailsSession();
    const first = await contacts.get(p.detailsToken!, venue.id, send);
    assert.equal(first.website, "https://example.com/venue");
    assert.equal(first.telephoneUrl, "tel:+12025550100");
    assert.deepEqual(await contacts.get(p.detailsToken!, venue.id, send), first);
    assert.equal((await (await fetch(`${base}/__test/counts`)).json()).details, 1);
    const lookup = await send("/api/starting-places", { method: "POST", body: JSON.stringify({ query: "Synthetic ZIP area" }) });
    assert.ok(lookup.ok);
    const matches = (await lookup.json()).matches;
    assert.equal(matches[1].precision, "postal_area");
    await scenario("normal");
    const located = await generateOuting("Bowling then dinner in Washington, DC for 2 people on 2026-11-07", EMPTY_PREFERENCES, { locationContext: { startingLocation: { point: { id: "authorized-start", coordinates: matches[1].coordinates }, explicitly_authorized: true, precision: "postal_area" }, maxFirstLegTravel: 10 } }, send);
    assert.equal(located.plans.length, 3);
    assert.equal(located.location, "Washington, DC");
    assert.equal(located.plans[0].firstLeg?.approximate, true);
    let strictValidated: ValidatedOuting | undefined;
    const strictResult = await generateOuting("Plan bowling and dinner in Baltimore on Saturday, November 7, 2026, for 2 people. Keep driving between venues under 5 minutes.", EMPTY_PREFERENCES, { onValidated: value => { strictValidated = value; } }, send);
    assert.equal(strictValidated?.request.maxLegTravel, 5);
    assert.equal(strictValidated?.request.maxLegTravelExclusive, true);
    assert.equal(strictValidated?.request.transport, "driving");
    assert.equal(strictResult.plans.length, 3);
    // Submitted manual text waits for explicit selection before any AI/planning.
    const confirmation = new StartingConfirmation();
    const manualSession = new StartingPlaceSession();
    const beforeStart = await (await fetch(`${base}/__test/counts`)).json();
    const waiting = confirmation.wait().then(origin => origin ? generateOuting("Bowling then dinner in Washington, DC for 2 people on 2026-11-07", EMPTY_PREFERENCES, { locationContext: origin }, send) : null);
    const found = await manualSession.get("union station, washington dc", send);
    assert.equal((await (await fetch(`${base}/__test/counts`)).json()).ai, beforeStart.ai);
    confirmation.confirm({ startingLocation: { point: { id: "authorized-start", coordinates: found[1].coordinates }, explicitly_authorized: true, precision: found[1].precision }, maxFirstLegTravel: 15 });
    const continued = await waiting;
    assert.equal(continued?.location, "Washington, DC");
    assert.equal(continued?.plans.length, 3);
    assert.equal(continued?.plans[0].firstLeg?.approximate, true);
    for (const state of ["lookup_disabled", "lookup_failure", "lookup_empty", "single_start"]) {
      await scenario(state);
      const lookupResponse = await send("/api/starting-places", { method: "POST", body: JSON.stringify({ query: "Synthetic station" }) });
      assert.equal(lookupResponse.ok, state === "lookup_empty" || state === "single_start");
      const payload = await lookupResponse.json();
      if (lookupResponse.ok) assert.equal(payload.matches.length, state === "single_start" ? 1 : 0);
      else assert.match(payload.message, /unavailable|could not complete/);
    }
    await scenario("sparse");
    const sparse = await generateOuting("Bowling then dinner in Baltimore for 2 people on 2026-11-07", EMPTY_PREFERENCES, {}, send);
    assert.equal(sparse.canDiscover, true);
    const beforeDiscovery = await (await fetch(`${base}/__test/counts`)).json();
    const moreVenues = await send("/api/plans/options", { method: "POST", body: JSON.stringify({ token: sparse.optionsToken, expandDiscovery: true }) });
    assert.equal(moreVenues.ok, true);
    const expandedData = await moreVenues.json();
    assert.deepEqual(expandedData.diagnostics.discoveredCounts, [10,10]);
    assert.equal((await (await fetch(`${base}/__test/counts`)).json()).searches - beforeDiscovery.searches, 2);
    assert.equal(adaptRanking(expandedData).canDiscover, false);
    await scenario("expanded");
    const expansionBaseline = await (await fetch(`${base}/__test/counts`)).json();
    const firstTwenty = await generateOuting("Bowling then dinner in Baltimore for 2 people on 2026-11-07", EMPTY_PREFERENCES, {}, send);
    const page = await send("/api/plans/options", { method: "POST", body: JSON.stringify({ token: firstTwenty.optionsToken, expandDiscovery: true }) });
    assert.equal(page.ok, true);
    const twentyData = await page.json();
    assert.deepEqual(twentyData.diagnostics.discoveredCounts, [20,20]);
    assert.equal(JSON.stringify(twentyData).includes("synthetic-next-page"), false);
    let twenty = expandedOptions(firstTwenty, adaptRanking(twentyData));
    const shown = new Set(firstTwenty.plans.map(p => p.venues.map(v => v.id).join("|")));
    const checkNew = () => { for (const p of twenty.plans) { const key = p.venues.map(v => v.id).join("|"); assert.equal(shown.has(key), false); shown.add(key); } };
    checkNew();
    for (let i = 0; i < 15; i++) {
      if (twenty.alternativeBatches?.length) twenty = nextOptions(twenty);
      else {
        const response = await send("/api/plans/options", { method: "POST", body: JSON.stringify({ token: twenty.optionsToken }) });
        assert.equal(response.ok, true); twenty = adaptRanking(await response.json());
      }
      assert.equal(twenty.plans.length, 3); checkNew();
    }
    const expandedUsage = await (await fetch(`${base}/__test/counts`)).json();
    assert.equal(expandedUsage.searches - expansionBaseline.searches, 4);
    assert.ok(expandedUsage.elements - expansionBaseline.elements <= 150);
    await scenario("bowling_diagnostic");
    const diagnosticRequest = "Bowling and dinner in Washington, DC on November 14, 2026, for 3 people. Keep driving between venues under 5 minutes.";
    const diagnosticInitial = await generateOuting(diagnosticRequest, EMPTY_PREFERENCES, {}, send);
    assert.ok(diagnosticInitial.notes.some(n => n.includes("bowling: 2 Google results")));
    const diagnosticMore = await send("/api/plans/options", { method: "POST", body: JSON.stringify({ token: diagnosticInitial.optionsToken, expandDiscovery: true }) });
    assert.equal(diagnosticMore.ok, true);
    const diagnosticData = await diagnosticMore.json();
    const funnel = diagnosticData.diagnostics.venuePipeline.bowling;
    assert.equal(funnel.googleResultsReceived, 11); assert.equal(funnel.geographyRejected, 1);
    assert.equal(funnel.duplicatesRemoved, 3); assert.equal(funnel.relevanceRejected, 1);
    assert.equal(funnel.eligibleRetained, 6); assert.equal(funnel.routeCompatibleVenues, 5);
    assert.equal(funnel.excludedByCheckedRouteFeasibility, 1); assert.equal(funnel.rankedVenues, 5);
    assert.equal(funnel.latestSearch.newEligibleMatches, 4); assert.equal(funnel.latestSearch.previouslyKnownMatches, 2);
    assert.ok(adaptRanking(diagnosticData).notes.some(n => n.includes("bowling: 11 Google results")));
    assert.equal(JSON.stringify(diagnosticData.diagnostics).includes("Fixture_"), false);
    await scenario("minute_pause");
    const paused = await generateOuting("Bowling then dinner in Baltimore for 2 people on 2026-11-07", EMPTY_PREFERENCES, {}, send);
    assert.equal(paused.plans.length, 0); assert.equal(paused.canExpand, true); assert.equal(paused.canDiscover, false);
    assert.ok(paused.optionsToken); assert.match(paused.message, /temporary routing limit/);
    for (const name of ["empty", "quota", "authentication"]) {
      await scenario(name);
      let retained: ValidatedOuting | undefined;
      const retryText = "Bowling then dinner in Baltimore for 2 people on 2026-11-07";
      const failure = await generateOuting(retryText, EMPTY_PREFERENCES, { onValidated: value => { retained = value; } }, send);
      assert.equal(failure.plans.length, 0);
      assert.match(failure.message, /matching real venues|destination could not be verified|capacity is temporarily unavailable|venue or routing service could not complete/);
      if (name === "quota") {
        assert.equal(failure.requestFailed, true);
        assert.ok(retained);
        const count = await (await fetch(`${base}/__test/counts`)).json();
        await scenario("normal");
        const recovered = await generateOuting(retryText, EMPTY_PREFERENCES, { continuation: retained.continuation }, send);
        assert.equal(recovered.plans.length, 3);
        assert.notEqual(recovered.requestFailed, true);
        assert.equal((await (await fetch(`${base}/__test/counts`)).json()).ai, count.ai, "retry reuses validated interpretation rather than another AI call");
      }
    }
    await scenario("location_first");
    const suggestedSession=new StartingAreaSession();
    let preparation=0;
    const spatial = await generateOuting("Plan bowling and dinner in Washington, DC on Saturday, November 14, 2026 for 3 people. Within 8 miles of Union Station.", EMPTY_PREFERENCES, {
      prepareOrigin:async input=>{
        preparation++;
        const response=await suggestedSession.get(input,send);
        assert.ok(response.matches.length>=1);
        assert.deepEqual(await suggestedSession.get(input,send),response);
        const match=response.matches[0];
        return {locationFirst:true,referenceToken:response.referenceToken,startingLocation:{point:{id:"reference_"+match.placeId,coordinates:match.coordinates},explicitly_authorized:true,precision:match.precision,source:"suggested",label:match.name}};
      }
    }, send);
    assert.equal(preparation,1);assert.equal(spatial.plans.length,3,spatial.message);
    assert.equal(spatial.location,"Washington, DC");
    assert.ok(spatial.plans.every(p=>p.firstLeg?.source==="suggested"&&p.firstLeg.miles!=null&&p.firstLeg.miles<=8));
    assert.ok(new Set(spatial.plans.map(p=>p.venues[0].id)).size>=2);
    await scenario("location_acceptance");
    const editor=new FirstPreference();const areas=new StartingAreaSession();
    const natural=await generateOuting("Plan bowling followed by dinner in Washington, DC, on Saturday, November 14, 2026, for 3 people. I'd prefer the first stop to be within 20 minutes of my starting point.",EMPTY_PREFERENCES,{
      prepareOrigin:async input=>{
        editor.hydrate(input.firstTravel);assert.equal(editor.value?.value,20);assert.equal(editor.value?.mode,"flexible");
        const choices=await areas.get(input,send);assert.equal(choices.matches.length,3);
        assert.ok(new Set(choices.matches.map(p=>p.reason)).size>=2);
        const p=choices.matches[0];
        return {locationFirst:true,firstTravel:editor.value,referenceToken:choices.referenceToken,startingLocation:{point:{id:"reference_"+p.placeId,coordinates:p.coordinates},explicitly_authorized:true,source:"suggested",precision:p.precision,label:p.name}};
      }
    },send);
    assert.equal(natural.plans.length,3,natural.message);assert.equal(editor.value?.value,20);
    assert.ok(natural.plans.some(p=>!p.firstLeg?.exceedsPreference),"Reuse checked onward venues so comparable preferred first stops remain useful.");
    assert.ok(natural.plans.every(p=>p.firstLeg?.minutes!=null&&p.firstLeg.minutes<=40));
    await scenario("partial");
    const partial = await generateOuting("Bowling then dinner in Baltimore for 2 people on 2026-11-07", EMPTY_PREFERENCES, {}, send);
    assert.equal(partial.plans.length, 1);
    await scenario("missing_routes");
    const unknown = await generateOuting("Bowling then dinner in Baltimore for 2 people on 2026-11-07", EMPTY_PREFERENCES, {}, send);
    assert.equal(unknown.plans[0].travel, null);
    const raw = await (await plan(new Request("http://localhost/api/plans/generate", { method: "POST", body: JSON.stringify({ activities: ["coffee"], date: "2026-11-07",startingLocation:{point:{id:"authorized-start",place_id:"Fixture_origin_0"},source:"manual",explicitly_authorized:true} }) }))).json();
    raw.dataMode = "mock";
    assert.throws(() => adaptRanking(raw), /Mixed venue data modes/);
    await scenario("mock");
    assert.equal((await (await mode()).json()).mode,"mock");
    const beforeMock=await (await fetch(`${base}/__test/counts`)).json();
    const mock=await generateOuting("Bowling then dinner in Baltimore for 2 people on 2026-11-07",EMPTY_PREFERENCES,{},send);
    assert.equal(mock.dataMode,"mock");assert.equal(mock.plans.length,3);
    const afterMock=await (await fetch(`${base}/__test/counts`)).json();
    for(const key of ["searches","elements","details"])assert.equal(afterMock[key],beforeMock[key]);
  } finally {
    backend.kill(); await once(backend, "exit");
    if (previous === undefined) delete process.env.BACKEND_URL; else process.env.BACKEND_URL = previous;
  }
});

test("contact session validates links, preserves failure without automatic retries, clears on regeneration", async () => {
  assert.equal(safeWebsite("javascript:alert(1)"), null);
  assert.equal(safeWebsite("https://user:pass@example.com"), null);
  let calls = 0;
  const send: typeof fetch = async () => { calls++; return Response.json({ message: "Quota reached" }, { status: 422 }); };
  const session = new VenueDetailsSession();
  await assert.rejects(session.get("token", "real-id", send), /Quota reached/);
  await assert.rejects(session.get("token", "real-id", send), /Quota reached/);
  assert.equal(calls, 1);
  session.clear();
  await assert.rejects(session.get("token", "real-id", send), /Quota reached/);
  assert.equal(calls, 2);
});
