import type { Plan } from "./planner";
// IDs only, page memory only. No storage API, coordinates or cross-user identity.
export class SurpriseHistory {
  private entries = new Map<string,number>();
  ids(now=Date.now()) {
    for(const [id,at] of this.entries)if(now-at>=600000)this.entries.delete(id);
    return [...this.entries.keys()];
  }
  record(plans:Plan[],now=Date.now()) {
    this.ids(now);
    for(const plan of plans)if(plan.planningMode==="surprise") {
      const id=plan.venues[0]?.providerPlaceId ?? plan.venues[0]?.id;
      if(id&&/^[A-Za-z0-9_-]{1,200}$/.test(id)){this.entries.delete(id);this.entries.set(id,now);}
    }
    while(this.entries.size>120)this.entries.delete(this.entries.keys().next().value!);
  }
  clear(){this.entries.clear();}
}
