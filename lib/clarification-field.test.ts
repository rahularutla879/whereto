import assert from "node:assert/strict";
import test from "node:test";
import * as React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { ClarificationField } from "../components/clarification-field";
import type { PendingOuting } from "./planning-client";

const render = (question: PendingOuting["questions"][number], value = "") =>
  renderToStaticMarkup(React.createElement(ClarificationField, { question, value, onChange: () => {} }));

test("date questions and correction attempts retain supported examples linked to the input", () => {
  for (const [question, value] of [["What day are you planning to go?", ""], ["Which date should we use?", "this weekend"]]) {
    const html = render({ field: "date", question, kind: value ? "ambiguous" : "essential" }, value);
    assert.ok(html.includes(question));
    assert.match(html, /aria-describedby="clarification-date-help"/);
    assert.match(html, /<small id="clarification-date-help"/);
    for (const example of ["tomorrow", "this Saturday", "next Friday", "Nov 11", "11 Nov 2026", "YYYY-MM-DD"]) {
      assert.ok(html.slice(html.indexOf("<small")).includes(example));
    }
    assert.doesNotMatch(html.slice(html.indexOf("<small")), /weekend/);
    if (value) assert.ok(html.includes(`value="${value}"`));
  }
});

test("other clarification fields retain their own wording without date guidance", () => {
  for (const field of ["location", "people", "activities", "time"] as const) {
    const question = `Confirm ${field}`;
    const html = render({ field, question, kind: "essential" }, "kept answer");
    assert.ok(html.includes(question));
    assert.match(html, /value="kept answer"/);
    assert.doesNotMatch(html, /clarification-date-help|tomorrow|this Saturday|next Friday|2026-11-07|<small/);
  }
});

test("year, weekend, past and invalid date questions render only their contextual guidance", () => {
  const cases = [
    { reason: "missing_year", question: "March 11 has already passed this year. Which year would you like to plan for?", helpText: "Enter a four-digit year, for example 2027." },
    { reason: "weekend", question: "Did you mean Saturday or Sunday?", helpText: "Reply Saturday or Sunday, or enter an exact date." },
    { reason: "past_date", question: "That date has already passed. Please choose today or a future date.", helpText: "Enter today or a future date, such as tomorrow or YYYY-MM-DD." },
    { reason: "invalid_date", question: "That date doesn't exist. Please enter a valid date.", helpText: "Check the day and month; include a year if needed." },
  ];
  for (const question of cases) {
    const html = render({ field: "date", kind: "ambiguous", ...question }, "2027");
    assert.ok(html.includes(question.helpText));
    assert.match(html, /aria-describedby="clarification-date-help"/);
    assert.doesNotMatch(html, /this Saturday|next Friday/);
    if (question.reason !== "weekend") assert.doesNotMatch(html, /Saturday or Sunday/);
    if (question.reason === "missing_year") {
      assert.match(html, /placeholder="YYYY"/);
      assert.doesNotMatch(html, /tomorrow/);
    }
  }
});

test("leap-year help and time help stay specific and accessible", () => {
  const leap = render({ field: "date", kind: "ambiguous", reason: "missing_year",
    question: "February 29 needs a leap year. Which year would you like to plan for?", helpText: "Enter a four-digit leap year." });
  assert.match(leap, /four-digit leap year/);
  assert.doesNotMatch(leap, /2027|Saturday or Sunday|tomorrow/);
  const time = render({ field: "time", kind: "ambiguous", reason: "invalid_time",
    question: "What overall time window do you mean? Include AM/PM.", helpText: "Use an overall window such as from 6 PM to 10 PM." });
  assert.match(time, /aria-describedby="clarification-time-help"/);
  assert.match(time, /from 6 PM to 10 PM/);
  assert.doesNotMatch(time, /id="clarification-date-help"|Nov 11|year|Saturday/);
});
