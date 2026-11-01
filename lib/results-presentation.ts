import type { Plan } from "./planner";

// Presentation only. Keep every request, result and calculation unchanged.
export const DEMO_DISCLOSURE = "Venues, prices, travel times, and event schedules are fictional.";
export const OPENING_HOURS_ISSUE = "Opening hours cannot be checked; obtain structured windows for the requested day.";

export function resultsSummary(count: number) {
  return `Found ${count} possible ${count === 1 ? "plan" : "plans"}.`;
}

export function consumerMessage(message: string) {
  if (/local.*Places.*minute/i.test(message)) return "We’ve reached a temporary search limit. Your saved plans are still available; try exploring again shortly.";
  if (/local.*(?:route|routing|provider).*minute|local rolling-minute/i.test(message))
    return "We've reached a temporary routing limit. You can still browse your saved plans and try exploring again shortly.";
  if (/Google.*quota|(?:Places|Routes|Place Details).*(?:quota|rate limit|element limit)/i.test(message))
    return "Google's current search or routing limit has been reached. Your saved recommendations are still available.";
  return message
    .replace(/\d+ confirmed mock recommendations; \d+ provisional alternatives\.\s*/g, "")
    .replace("No candidate satisfies all known limits. Review rejection reasons and adjust the relevant constraint.", "No plan fits all your current preferences. Try adjusting a limit or choosing different activities.")
    .replace("No confirmed recommendation. Obtain the missing evidence listed in provisional alternatives.", "Some details still need checking before you go.")
    .replaceAll(OPENING_HOURS_ISSUE, "Opening hours have not been checked. Check them before you go.")
    .replaceAll("availability cannot be checked; obtain structured windows for the requested day.", "Availability for this plan has not been checked. Confirm each stop can host your group at these times.")
    .replaceAll("Obtain group capacity before confirming this stop.", "Check that this stop can accommodate your group.")
    .replaceAll("Schedule provenance is unknown; obtain schedule evidence before confirmation.", "The schedule has not been checked. Confirm the times before choosing this plan.")
    .replaceAll("Travel evidence is missing; obtain a travel estimate before confirming timing.", "Travel time has not been checked. Confirm you can get between the stops in time.")
    .replaceAll("Obtain the activity duration before confirming the schedule.", "Check how long this activity takes before relying on the schedule.")
    .replaceAll("Price is incomplete or unsourced; obtain a price before confirming costs.", "Some prices have not been checked. Confirm the cost before choosing this plan.")
    .replaceAll("Mock travel is mode-independent; no real route or mode-specific time is verified.", "Travel times are sample estimates and do not change with your chosen transport.")
    .replaceAll("openingHours", "opening hours")
    .replaceAll("groupBudget", "the total group budget")
    .replaceAll("maxLegTravel", "the travel limit between two stops")
    .replaceAll("Known activity costs exceed budget", "Estimated activity costs exceed your per-person budget")
    .replaceAll("Known activity costs exceed the total group budget", "Estimated activity costs exceed your total group budget")
    .replace(/No mock records/g, "No sample activities")
    .replace(/\b(?:shared-catalog|Shared catalog|shared catalog|fictional catalog)\b/g, "sample data")
    .replace(/\b(?:candidate|Candidate)\b/g, "plan")
    .replace(/\bfixture\b/g, "sample")
    .replace(/AI interpretation or Python planner unavailable[^.]*\./g, "We could not create your plans. Please try again.")
    .replace(/Python planner unavailable[^.]*\./g, "We could not create your plans. Please try again.")
    .replace(/AI interpretation unavailable[^.]*\./g, "We could not read your request just now. Please try again.")
    .replace(/(?:Start the (?:Python )?backend and local AI service|Start the backend|Check both services|Check the local AI service and settings),? (?:then )?(?:and )?(?:try again|retry)\./g, "")
    .replaceAll("AI suggestions, not requested stops:", "Suggested activities to choose from:")
    .replace(/AI (?:could not|did not)/g, "We could not")
    .replace(/AI may have omitted/g, "We may have missed")
    .replace(/AI returned/g, "We could not verify")
    .replaceAll("Manual people overrides the text interpretation.", "Using the group size you selected.")
    .replace(/Manual (\w+) overrides the text interpretation\./g, "Using your selected $1.")
    .replace(/\s+/g, " ").trim();
}

export function failureMessage(message: string) {
  // Routine unchecked hours are already in About these estimates; keep the
  // actual failed constraint here, with a fallback for an otherwise empty error.
  return consumerMessage(message.replaceAll(OPENING_HOURS_ISSUE, ""))
    || "We could not find a plan for this request. Try adjusting your preferences or choosing different activities.";
}

export function estimateNotes(notes: string[]) {
  // These known system notes are replaced by the single disclosure/estimates
  // area. Keep all other notes, including suggestions and manual selections.
  const boilerplate = /^(?:AI interpretation; itinerary calculations|All shared-catalog venues|Shared catalog data is fictional|Costs exclude transport|Travel excludes the first\/last trip|Confirmed means constraints checked)/;
  return [...new Set(notes.filter(note => !boilerplate.test(note)).map(consumerMessage))];
}

export function planWarnings(plan: Plan): string[] {
  if (plan.dataMode === "real") {
    const routine = new Set(["approximate_destination", "unknown_price", "unknown_capacity", "unknown_duration", "unknown_openingHours", "unknown_schedule_evidence", "uncertain_timing", "missing_transfer_schedule", "unverified_availability", "unverified_dinner", "unverified_budget", "session_not_verified"]);
    const warnings = (plan.constraintIssues ?? []).filter(issue => {
      if(plan.travelClassification==='outside_preference' && plan.travelDeviations?.length && ['extra_first_travel','extra_between_travel'].includes(issue.code??'') && issue.status!=='violation')return false;
      return true;
    }).filter(issue => issue.status === "violation" || (!routine.has(issue.code ?? "") && !(issue.status === "unknown" && issue.field === "hours"))).map(issue => consumerMessage(issue.message));
    if (plan.hardBudget || plan.issues.some(issue => issue.includes("Your hard budget"))) warnings.push("Your hard budget cannot be verified because venue prices are unavailable. This plan has not passed the budget constraint.");
    if (plan.travel === null || plan.legs.some(leg => leg.minutes === null)) warnings.push("Travel time is missing for a required leg; travel constraints are not fully verified.");
    return [...new Set(warnings)];
  }
  // Only the routine missing-opening-hours disclosure moves to the common
  // estimates section. Every other issue (including future conflicts) stays by
  // its plan, visible even while itinerary details are closed.
  const warnings = plan.issues.filter(issue => issue !== OPENING_HOURS_ISSUE).map(consumerMessage);
  if (plan.price === null || plan.prices.some(q => q.amount === null)) {
    warnings.push("Some prices are unknown, so the total cost and fit with your budget still need checking.");
  }
  if (plan.travel === null || plan.legs.some(leg => leg.minutes === null)) {
    warnings.push("Travel time is unknown, so check whether you can get between these stops in time.");
  }
  if (plan.duration === null || plan.stops.some(stop => stop.start === null || stop.end === null || stop.venue.duration === null)) {
    warnings.push("Some timings are unknown. Check the schedule before choosing this plan.");
  }
  return [...new Set(warnings)];
}
