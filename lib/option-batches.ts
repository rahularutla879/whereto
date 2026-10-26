import type { PlannerResult } from "./planner";

// Consume already evaluated options once; never resubmit or relax constraints.
export function nextOptions(result: PlannerResult): PlannerResult {
  const [next, ...remaining] = result.alternativeBatches ?? [];
  return next ? { ...result, plans: next, alternativeBatches: remaining } : result;
}

// An early explicit search must not discard still-unviewed, checked options.
export function expandedOptions(previous: PlannerResult, next: PlannerResult): PlannerResult {
  return { ...next, alternativeBatches: [...(previous.alternativeBatches ?? []), ...(next.alternativeBatches ?? [])] };
}
