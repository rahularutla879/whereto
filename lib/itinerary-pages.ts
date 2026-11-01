import type { PlannerResult, Plan } from "./planner";

export const BEYOND_NOTICE = "These options exceed your preferred travel range. You can still explore them if you're comfortable traveling farther.";
export function beyondNotice(result:PlannerResult):string{
 const kinds=new Set(result.plans.map(p=>p.travelClassification??'matching'));
 const mixed=kinds.size>1;
 if(kinds.has('beyond_limit'))return `${mixed?'Some options':'These options'} exceed a hard travel limit and are shown only under your explicit opt-in. Review each option's verified exceptions.`;
 if(kinds.has('unverified'))return `${mixed?'Some options have':'These options have'} unverified travel requirements. Check each option's evidence before choosing.`;
 return mixed?"Some options exceed your preferred travel range. Check each option before choosing to travel farther.":BEYOND_NOTICE;
}
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
