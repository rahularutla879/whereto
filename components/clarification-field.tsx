import * as React from "react";
import type { PendingOuting } from "../lib/planning-client";

// Shared by the initial question and correction attempts; no date parsing here.
export function ClarificationField({ question, value, onChange }: {
  question: PendingOuting["questions"][number];
  value: string;
  onChange: (value: string) => void;
}) {
  const help = question.helpText ?? (question.field === "date" && !question.reason
    ? "Try tomorrow, this Saturday, next Friday, Nov 11, 11 Nov 2026, or YYYY-MM-DD." : undefined);
  const helpId = help ? `clarification-${question.field}-help` : undefined;
  return <div><label>
    <span>{question.question}</span>
    <input aria-label={question.question} aria-describedby={helpId} type="text"
      maxLength={question.field === "activities" ? 500 : question.field === "time" ? 150 : 80}
      value={value} placeholder={question.field === "location" ? "City or location" : question.field === "people" ? "e.g. 4" : question.reason === "missing_year" ? "YYYY" : question.reason === "weekend" ? "Saturday or Sunday" : question.field === "date" ? "e.g. Nov 11 or 2026-11-11" : question.field === "activities" ? "e.g. coffee, museum, then coffee" : "e.g. from 6 PM to 10 PM"}
      onChange={event => onChange(event.target.value)} />
    {helpId && <small id={helpId} className="clarification-date-help">{help}</small>}
  </label>{question.field==='activities'&&<a href="/supported-activities" target="_blank" rel="noopener noreferrer">View supported activities<span className="sr-only"> (opens in a new tab)</span></a>}</div>;
}
