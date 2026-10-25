import type { PlannerResult } from "./planner";

// Consume already evaluated options once; never resubmit or relax constraints.
export function nextOptions(result: PlannerResult): PlannerResult {
  const [next, ...remaining] = result.alternativeBatches ?? [];
  return next ? { ...result, plans: next, alternativeBatches: remaining } : result;
}
