import type { PlannerResult, Plan } from "./planner";

export const BEYOND_NOTICE = "These additional itineraries don't meet all your original requirements. We're showing them so you can explore more options.";
export function signature(plan: Plan): string {
  return JSON.stringify(plan.venues.map(v => [v.activity, v.providerPlaceId ?? v.id]));
}
export function beyondPage(result: PlannerResult): boolean {
  return result.plans.some(p => p.travelClassification && p.travelClassification !== "matching");
}
/** In-memory only. Arrows read immutable snapshots and never perform I/O. */
export class ItineraryPages {
  pages: PlannerResult[] = [];
  index = 0;
  private seen = new Set<string>();
  reset() { this.pages = []; this.index = 0; this.seen.clear(); }
  append(result: PlannerResult): boolean {
    const identities = new Set(this.seen);
    const plans = result.plans.filter(p => {
      const id = signature(p);
      if (identities.has(id)) return false;
      identities.add(id); return true;
    });
    if (!plans.length) return false;
    this.seen = identities;
    this.pages.push(structuredClone({ ...result, plans }));
    this.index = this.pages.length - 1;
    return true;
  }
  navigate(delta: -1 | 1): PlannerResult | undefined {
    const index = this.index + delta;
    if (index < 0 || index >= this.pages.length) return undefined;
    this.index = index;
    return structuredClone(this.pages[index]);
  }
}
