import * as React from "react";
import type { PendingOuting } from "../lib/planning-client";

// Shared by the initial question and correction attempts; no date parsing here.
export function ClarificationField({ question, value, onChange }: {
  question: PendingOuting["questions"][number];
  value: string;
  onChange: (value: string) => void;
}) {
  const dateHelpId = question.field === "date" ? "clarification-date-help" : undefined;
  return <label>
    <span>{question.question}</span>
    <input aria-label={question.question} aria-describedby={dateHelpId} type="text"
      maxLength={question.field === "activities" ? 500 : question.field === "time" ? 150 : 80}
      value={value} placeholder={question.field === "location" ? "City or location" : question.field === "people" ? "e.g. 4" : question.field === "date" ? "e.g. tomorrow or 2026-11-07" : question.field === "activities" ? "e.g. coffee, museum, then coffee" : "e.g. from 6 PM to 10 PM"}
      onChange={event => onChange(event.target.value)} />
    {dateHelpId && <small id={dateHelpId} className="clarification-date-help">
      You can type “tomorrow”, “this Saturday”, “next Friday”, or a date like “November 7, 2026” or “2026-11-07”.
    </small>}
  </label>;
}
