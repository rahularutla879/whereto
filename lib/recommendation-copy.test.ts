import assert from "node:assert/strict";
import test from "node:test";
import { recommendationCopy, type RecommendationFacts } from "./recommendation-copy";

const venue = (id: string, name = id) => ({ id, name });
const plan = (id: string, values: Partial<RecommendationFacts> = {}): RecommendationFacts => ({
  score: 0.5, quality: 0.5, cost: 40, travel: 20, venues: [venue(id)], ...values,
});

test("labels follow actual results rather than option positions", () => {
  const cheap = plan("Cafe", { score: 0.4, quality: 0.2, cost: 20, travel: 25 });
  const quick = plan("Museum", { score: 0.5, quality: 0.5, cost: 60, travel: 5 });
  const best = plan("Gallery", { score: 0.9, quality: 0.9, cost: 80, travel: 20 });
  for (const ordered of [[cheap, quick, best], [best, cheap, quick], [quick, best, cheap]]) {
    const copy = recommendationCopy(ordered, "experience");
    assert.equal(copy[ordered.indexOf(cheap)].label, "LOWEST COST");
    assert.match(copy[ordered.indexOf(cheap)].description, /\$20\.00 per person/);
    assert.equal(copy[ordered.indexOf(quick)].label, "SHORTEST TRAVEL");
    assert.match(copy[ordered.indexOf(quick)].description, /5 minutes between stops/);
    assert.equal(copy[ordered.indexOf(best)].label, "TOP MATCH");
    assert.match(copy[ordered.indexOf(best)].description, /Best Experience.*highest sample venue quality/);
  }
});

test("equal coffee itineraries acknowledge the ordering difference without invented benefits", () => {
  const sunday = venue("coffee-1", "Sunday Kind Café");
  const paper = venue("coffee-2", "Paper Cup Studio");
  const wonder = venue("museum-2", "The Wonder Collection");
  const harbor = venue("museum-1", "Harbor Discovery Hall");
  const options = [
    plan("a", { score: 0.9, quality: 1, cost: 41, travel: 18, venues: [sunday, wonder, paper] }),
    plan("b", { score: 0.9, quality: 1, cost: 41, travel: 18, venues: [paper, wonder, sunday] }),
    plan("c", { score: 0.25, quality: 0, cost: 31, travel: 18, venues: [sunday, harbor, paper] }),
  ];
  const copy = recommendationCopy(options, "experience");
  assert.equal(copy[0].label, "JOINT TOP MATCH");
  assert.match(copy[0].description, /Sunday Kind Café/);
  assert.equal(copy[1].label, "DIFFERENT STOP ORDER");
  assert.match(copy[1].description, /Same cost, travel and sample quality as Option 1; starts at Paper Cup Studio/);
  assert.equal(copy[2].label, "LOWEST COST");
  assert.match(copy[2].description, /\$31\.00.*Harbor Discovery Hall/);
  assert.doesNotMatch(copy.map(c => c.description).join(" "), /shortest/);
  assert.equal(new Set(copy.map(c => c.description)).size, 3);
});

test("highest sample quality is identified independently of highest overall preference score", () => {
  const copy = recommendationCopy([
    plan("a", { score: 0.9, quality: 0.8, cost: 60, travel: 20 }),
    plan("b", { score: 0.4, quality: 0.1, cost: 20, travel: 30 }),
    plan("c", { score: 0.3, quality: 0.2, cost: 40, travel: 5 }),
    plan("d", { score: 0.5, quality: 1, cost: 80, travel: 25 }),
  ], "balanced");
  assert.equal(copy[3].label, "TOP SAMPLE VENUES");
  assert.match(copy[3].description, /Highest sample venue quality of these plans/);
  assert.match(copy[0].description, /Balanced/);
  assert.doesNotMatch(copy[0].description, /highest sample venue quality/);
});

test("ties distinguish changed venues, changed intermediate order and exact duplicates honestly", () => {
  const equal = recommendationCopy([plan("One"), plan("Two"), plan("Three")], "budget");
  assert.equal(equal[1].label, "DIFFERENT VENUES");
  assert.match(equal[1].description, /Same cost, travel and sample quality.*includes Two/);
  assert.match(equal[0].description, /Joint best fit for Budget-friendly/);
  assert.doesNotMatch(equal.map(c => c.description).join(" "), /lowest cost|shortest|highest sample/);
  const duplicate = recommendationCopy([plan("One"), plan("One")], "balanced");
  assert.equal(duplicate[1].label, "ANOTHER OPTION");
  assert.match(duplicate[1].description, /Same venues, cost, travel and sample quality/);
  const reordered = recommendationCopy([
    plan("a", { venues: [venue("start"), venue("middle"), venue("end")] }),
    plan("b", { venues: [venue("start"), venue("end"), venue("middle")] }),
  ], "balanced");
  assert.match(reordered[1].description, /visits end at stop 2/);
});

test("unknown comparison data and a lone result cannot justify superlatives", () => {
  const partial = plan("Unknown", { score: null, quality: null, cost: null, travel: null });
  const options = [plan("Known"), partial];
  const copy = recommendationCopy(options, "experience");
  assert.ok(copy.every(c => c.label === "ALTERNATIVE PLAN"));
  assert.doesNotMatch(copy.map(c => c.description).join(" "), /best|lowest|shortest|highest|same cost/i);
  assert.match(copy[0].description, /\$40\.00 per person and 20 minutes/);
  assert.equal(recommendationCopy([partial], "budget")[0].label, "YOUR ITINERARY");
  assert.equal(recommendationCopy([{ ...partial, venues: [] }], "budget")[0].description, "An option for the activities you requested.");
});

test("joint cost and travel winners are labeled as ties when other characteristics differ", () => {
  const copy = recommendationCopy([
    plan("top", { score: 0.9, quality: 1, cost: 80, travel: 30 }),
    plan("cheap-a", { score: 0.5, quality: 0.5, cost: 20, travel: 10 }),
    plan("cheap-b", { score: 0.4, quality: 0.4, cost: 20, travel: 15 }),
  ], "budget");
  assert.equal(copy[1].label, "JOINT LOWEST COST");
  assert.equal(copy[2].label, "JOINT LOWEST COST");
  assert.match(copy[1].description, /tied for the lowest cost/);
  const travel = recommendationCopy([
    plan("top", { score: 0.9, cost: 40, travel: 20 }),
    plan("a", { score: 0.5, cost: 60, travel: 10 }),
    plan("b", { score: 0.4, cost: 70, travel: 10 }),
  ], "balanced");
  assert.equal(travel[1].label, "JOINT SHORTEST TRAVEL");
  assert.equal(travel[2].label, "JOINT SHORTEST TRAVEL");
});
