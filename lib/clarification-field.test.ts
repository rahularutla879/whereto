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
    for (const example of ["tomorrow", "this Saturday", "next Friday", "November 7, 2026", "2026-11-07"]) {
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
