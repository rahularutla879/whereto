import assert from "node:assert/strict";
import test from "node:test";
import { EMPTY_PREFERENCES, EXAMPLE_REQUEST, makePlans, legTravel, type Preferences } from "./planner";
import { CATALOG, type Activity } from "./mock-data";
import { resolveDate } from "./request";

const context = { today: "2026-11-01" };
const plan = (request: string, changes: Partial<Preferences> = {}) => makePlans(request, { ...EMPTY_PREFERENCES, ...changes }, context);

function checkActivities(request: string, expected: Activity[]) {
  const result = plan(request);
  assert.ok(result.plans.length > 0, result.message);
  for (const option of result.plans) assert.deepEqual(option.venues.map((v) => v.activity), expected);
  return result;
}

test("original example still gives three deterministic, distinct matching plans", () => {
  const result = checkActivities(EXAMPLE_REQUEST, ["bowling", "drinks", "movie"]);
  assert.equal(result.plans.length, 3);
  assert.equal(new Set(result.plans.map((p) => p.id)).size, 3);
  assert.deepEqual(result, plan(EXAMPLE_REQUEST));
  result.plans.forEach((p) => { assert.equal(p.people, 4); assert.equal(p.date, "2026-11-07"); });
});

const requests: [string, Activity[]][] = [
  ["Dinner and karaoke in Baltimore", ["food", "karaoke"]],
  ["Coffee and art in Baltimore tomorrow", ["coffee", "art"]],
  ["An art museum and a walk in Baltimore", ["museum", "outdoors"]],
  ["Hiking and a picnic in Baltimore", ["hiking", "picnic"]],
  ["Arcade and escape room in Baltimore", ["arcade", "escape"]],
  ["Mini golf and shopping in Baltimore", ["miniGolf", "shopping"]],
  ["Zoo and ice skating in Baltimore", ["zoo", "skating"]],
  ["Outdoor activities and lunch in Baltimore", ["outdoors", "food"]],
  ["A baseball game in Baltimore on 2026-11-07", ["baseball"]],
  ["Basketball in Baltimore on 2026-11-07", ["basketball"]],
  ["Football in Baltimore on 2026-11-07", ["football"]],
  ["Soccer match in Baltimore on 2026-11-07", ["soccer"]],
  ["Hockey in Baltimore on 2026-11-07", ["hockey"]],
  ["Sporting event in Baltimore on 2026-11-07", ["sports"]],
  ["A concert in Baltimore on 2026-11-07", ["concert"]],
  ["Theatre in Baltimore on 2026-11-07", ["theater"]],
  ["A musical in Baltimore on 2026-11-07", ["musical"]],
  ["Ballet in Baltimore on 2026-11-07", ["ballet"]],
  ["Opera in Baltimore on 2026-11-07", ["opera"]],
  ["Comedy show in Baltimore on 2026-11-07", ["comedy"]],
];
for (const [request, expected] of requests) test(`recognizes: ${request}`, () => { checkActivities(request, expected); });

test("every catalog category has a tested request", () => {
  const covered = new Set([...requests.flatMap(([, categories]) => categories), "bowling", "drinks", "movie"]);
  for (const activity of Object.keys(CATALOG)) assert.ok(covered.has(activity), activity);
});

for (const request of ["", "Surprise me", "Skydiving", "Dinner and skydiving", "Karaoke and scuba diving", "Bowling and axe throwing", "Tennis on 2026-11-07", "Concert or theater on 2026-11-07", "Dinner without drinks", "Concert after dinner on 2026-11-07"]) {
  test(`unsupported/ambiguous request never creates an unrelated partial plan: ${request || "empty"}`, () => {
    const result = plan(request);
    assert.equal(result.plans.length, 0);
    assert.ok(result.message.length > 20);
  });
}

test("more than four activities are not silently truncated", () => {
  const result = plan("Bowling, drinks, movie, coffee and art");
  assert.equal(result.plans.length, 0);
  assert.match(result.message, /four activities/);
});
test("scheduled events need a date, including vague weekends", () => {
  for (const request of ["Baseball", "A concert this weekend", "Theater"]) {
    const result = plan(request);
    assert.equal(result.plans.length, 0);
    assert.match(result.message, /exact date/);
  }
});
test("missing event date blocks whole request instead of returning dinner alone", () => {
  const result = plan("Dinner and concert on 2026-11-08");
  assert.equal(result.plans.length, 0);
  assert.match(result.message, /No mock concert is scheduled on 2026-11-08/);
});
test("baseball cannot be substituted with other sports or an unscheduled venue", () => {
  const result = plan("Baseball game on 2026-11-07");
  assert.ok(result.plans.length);
  for (const option of result.plans) for (const v of option.venues) {
    assert.equal(v.kind, "event");
    assert.equal(v.activity, "baseball");
    if (v.kind === "event") assert.equal(v.eventDate, "2026-11-07");
  }
  assert.equal(plan("Baseball on 2026-11-08").plans.length, 0);
});
test("event date preference overrides request date and missing schedule is not fabricated", () => {
  assert.ok(plan("Concert on 2026-11-08", { date: "2026-11-07" }).plans.length);
  assert.equal(plan("Concert on 2026-11-07", { date: "2026-11-08" }).plans.length, 0);
});
test("relative and named dates resolve against explicit reference day", () => {
  assert.equal(plan("Baseball this Saturday").plans[0].date, "2026-11-07");
  assert.equal(plan("Concert on November 14, 2026").plans[0].date, "2026-11-14");
  assert.equal(resolveDate("tomorrow", "", "2026-11-06").date, "2026-11-07");
  assert.equal(resolveDate("next Saturday", "", "2026-11-07").date, "2026-11-14");
});
test("invalid or multiple dates require correction", () => {
  for (const request of ["Concert on 2026-02-30", "Concert on November 31, 2026", "Concert Saturday and Sunday", "Concert on 2026-11-07 and 2026-11-14"]) assert.equal(plan(request).plans.length, 0, request);
  assert.equal(plan("Concert", { date: "not-a-date" }).plans.length, 0);
});
test("regular venues do not require a scheduled event date", () => {
  const result = plan("Museum and coffee on 2026-11-08");
  assert.ok(result.plans.length);
  result.plans.forEach((p) => p.venues.forEach((v) => assert.equal(v.kind, "venue")));
});
test("event times, stop durations, travel, and waiting are respected", () => {
  const result = plan("Baseball and concert on 2026-11-07");
  assert.ok(result.plans.length);
  for (const option of result.plans) {
    option.stops.forEach((stop, i) => {
      assert.equal(stop.end - stop.start, stop.venue.duration);
      if (stop.venue.kind === "event") assert.equal(stop.start, stop.venue.start);
      if (i) assert.ok(stop.start >= option.stops[i - 1].end + legTravel(option.stops[i - 1].venue, stop.venue));
    });
    assert.equal(option.duration, option.stops.at(-1)!.end - option.stops[0].start);
    assert.equal(option.duration, 420);
  }
});
test("overlapping performances and impossible activity orders are rejected", () => {
  assert.equal(plan("Concert and theater on 2026-11-07").plans.length, 0);
  assert.equal(plan("Dinner and baseball on 2026-11-07").plans.length, 0);
  assert.ok(plan("Baseball and dinner on 2026-11-07").plans.length);
});
test("budget changes recommendations and caps every plan", () => {
  const unrestricted = plan("Dinner and karaoke");
  const restricted = plan("Dinner and karaoke", { budget: "25" });
  assert.ok(restricted.plans.length);
  assert.notEqual(unrestricted.plans[0].id, restricted.plans[0].id);
  restricted.plans.forEach((p) => assert.ok(p.price <= 25));
  assert.equal(plan("Dinner and karaoke", { budget: "1" }).plans.length, 0);
  const parsed = plan("Dinner and karaoke under $25 per person");
  assert.ok(parsed.plans.length);
  parsed.plans.forEach((p) => assert.ok(p.price <= 25));
});
test("travel cap changes recommendations and is never ignored", () => {
  const flexible = plan("Bowling and drinks", { budget: "30" });
  const strict = plan("Bowling and drinks", { budget: "30", travel: "5" });
  assert.ok(strict.plans.length);
  assert.notEqual(flexible.plans[0].id, strict.plans[0].id);
  strict.plans.forEach((p) => assert.ok(p.travel <= 5));
  assert.equal(plan("Bowling and drinks", { travel: "0" }).plans.length, 0);
  assert.ok(plan("Bowling", { travel: "0" }).plans.length);
});
test("group size filters both regular venue and event mock capacity", () => {
  for (const request of ["Dinner and karaoke", "Baseball on 2026-11-07"]) {
    const small = plan(request, { people: "4", cost: "budget" });
    const large = plan(request, { people: "12", cost: "budget" });
    assert.ok(large.plans.length);
    assert.notEqual(small.plans[0].id, large.plans[0].id);
    large.plans.forEach((p) => p.venues.forEach((v) => assert.ok(v.capacity >= 12)));
    assert.equal(plan(request, { people: "21" }).plans.length, 0);
    assert.equal(plan(request, { people: "12", budget: "30" }).plans.length, 0);
  }
});
test("experience preference changes actual first recommendation, within hard constraints", () => {
  const cheap = plan("Dinner and karaoke", { cost: "budget" });
  const premium = plan("Dinner and karaoke", { cost: "experience" });
  assert.notEqual(cheap.plans[0].id, premium.plans[0].id);
  assert.ok(cheap.plans[0].price < premium.plans[0].price);
  const restricted = plan("Dinner and karaoke", { cost: "experience", budget: "25" });
  assert.ok(restricted.plans.length);
  restricted.plans.forEach((p) => assert.ok(p.price <= 25));
});
test("zero budget only permits free mock activities and options remain distinct", () => {
  const result = plan("Art and outdoors", { budget: "0" });
  assert.ok(result.plans.length);
  assert.equal(new Set(result.plans.map((p) => p.id)).size, result.plans.length);
  result.plans.forEach((p) => assert.equal(p.price, 0));
  assert.equal(plan("Baseball on 2026-11-07", { budget: "0" }).plans.length, 0);
});
test("invalid preferences are rejected rather than silently replaced", () => {
  for (const changes of [{people:"0"}, {people:"2.5"}, {people:"101"}, {budget:"-1"}, {budget:"abc"}, {travel:"-1"}, {travel:"1.5"}]) assert.equal(plan("Dinner", changes).plans.length, 0);
});
test("unsupported locations remain unsupported, explicit override works", () => {
  assert.equal(plan("Dinner in Boston").plans.length, 0);
  assert.equal(plan(EXAMPLE_REQUEST, { location: "New York" }).plans.length, 0);
  assert.ok(plan("Dinner in Boston", { location: "Baltimore" }).plans.length);
  assert.ok(plan("Dinner in Baltimore, MD").plans.length);
});
