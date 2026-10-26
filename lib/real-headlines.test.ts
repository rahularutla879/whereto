import assert from "node:assert/strict";
import test from "node:test";
import { realHeadlines } from "./real-headlines";
import type { Activity } from "./mock-data";
const venue = (name: string, activity: Activity, address?: string) => ({ name, activity, address });

test("two-stop real headlines use actual venue pairs and simple activity eyebrows", () => {
  const pairs = [[venue("Fixture Lanes", "bowling"), venue("Fixture Kitchen", "food")], [venue("Other Lanes", "bowling"), venue("Other Kitchen", "food")]];
  const headings = realHeadlines(pairs, [1]);
  assert.equal(headings[0].title, "Fixture Lanes & Fixture Kitchen");
  assert.equal(headings[0].label, "OPTION 1 · BOWLING + DINNER");
  assert.equal(headings[1].label, "OPTION 2 · BOWLING + DINNER");
  assert.notEqual(headings[0].title, headings[1].title);
  assert.doesNotMatch(JSON.stringify(headings), /provisional|best|cheapest|premium|top rated|open now/i);
});

test("three-stop headlines preserve ordered venue highlights and repeated activities", () => {
  const headings = realHeadlines([[venue("First Café", "coffee"), venue("Gallery", "art"), venue("Second Café", "coffee")]]);
  assert.equal(headings[0].title, "First Café · Gallery · Second Café");
  assert.equal(headings[0].label, "OPTION 1 · COFFEE + ART GALLERY + COFFEE");
});

test("four-stop headlines remain bounded with full names retained separately", () => {
  const names = ["An unusually long synthetic bowling establishment", "Another unusually long synthetic coffee establishment", "A third unusually long synthetic museum establishment", "A fourth unusually long synthetic dinner establishment"];
  const headings = realHeadlines([[venue(names[0], "bowling"), venue(names[1], "coffee"), venue(names[2], "museum"), venue(names[3], "food")]], [3]);
  assert.ok(Array.from(headings[0].title).length <= 121);
  assert.equal(headings[0].title.split(" · ").length, 4);
  assert.equal(headings[0].fullTitle, names.join(" & "));
  assert.equal(headings[0].label, "OPTION 1 · BOWLING + COFFEE + MUSEUM + DINNER");
});

test("long two-stop names are preserved, and colliding abbreviations expand truthfully", () => {
  const a = "Identical very long establishment prefix AAA CommonTail";
  const b = "Identical very long establishment prefix BBB CommonTail";
  const pair = realHeadlines([[venue(a, "bowling"), venue(b, "food")]]);
  assert.equal(pair[0].title, `${a} & ${b}`);
  const options = [a, b].map(name => [venue(name, "coffee"), venue("Museum", "museum"), venue("Kitchen", "food")]);
  const headings = realHeadlines(options);
  assert.notEqual(headings[0].title, headings[1].title);
  assert.ok(headings.every(h => !h.title.includes("…")));
});

test("same-named businesses can be distinguished with supplied addresses without inventing dinner", () => {
  const headings = realHeadlines(["1 Synthetic Street", "2 Synthetic Street"].map(address => [venue("Café", "coffee", address), venue("Kitchen", "food")]));
  assert.notEqual(headings[0].title, headings[1].title);
  assert.match(headings[0].title, /1 Synthetic Street/);
  assert.equal(headings[0].label, "OPTION 1 · COFFEE + FOOD");
});
