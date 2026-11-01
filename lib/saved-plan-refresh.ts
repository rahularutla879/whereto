export type RefreshedVenue={status:string;name?:string;address?:string;mapsUrl?:string|null;phone?:string|null;telephoneUrl?:string|null;website?:string|null;businessStatus?:string;message?:string;refreshedAt?:string;attributions?:{provider?:string|null;uri?:string|null}[]};
export function mergeRefreshed(previous:Record<string,RefreshedVenue>,updates:Record<string,RefreshedVenue>){
 const merged={...previous};
 for(const [id,value] of Object.entries(updates)){
  const old=previous[id];
  merged[id]=value.status==="refreshed"||!old?.name?value:value.status==="already_attempted"?old:{...old,status:"stale",message:value.message};
 }
 return merged;
}
