import * as React from "react";
import { DEMO_DISCLOSURE, estimateNotes } from "../lib/results-presentation";

export function ResultsInformation({ notes, needsChecking, real = false }: { notes: string[]; needsChecking: boolean; real?: boolean }) {
  const extraNotes = estimateNotes(notes);
  if (real) return <aside className="results-information" aria-label="About these real results"><p>Real venues from <span translate="no">Google Maps</span>. Check venue hours and suitability before going. Suggested stops are not bookings or a confirmed schedule.</p><details className="estimates-details"><summary>About these estimates</summary><ul>{extraNotes.map(note => <li key={note}>{note}</li>)}</ul></details></aside>;
  return <aside className="results-information" aria-label="About these sample results">
    <p>{DEMO_DISCLOSURE}{needsChecking && " Opening hours and availability still need checking."}</p>
    <details className="estimates-details">
      <summary>About these estimates</summary>
      <ul>
        <li>Opening hours and availability have not been verified. Check directly before you go; these plans are not bookings.</li>
        <li>Prices cover sample activities only. Transport fares, taxes, tips, booking fees and extras are excluded. Shopping purchases are extra; the free picnic option requires bringing your own food.</li>
        <li>Travel times are made-up estimates between stops, not real routes. They exclude getting to the first stop and returning home, and do not change with your chosen transport.</li>
        <li>Times are samples too. Total outing time includes waiting between activities.</li>
        {extraNotes.map(note => <li key={note}>{note}</li>)}
      </ul>
    </details>
  </aside>;
}
