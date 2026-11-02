export type RefreshedVenue={hoursEvidence?:import("./venue-hours").HoursEvidence;status:string;reason?:string;retryable?:boolean;retryAfterSeconds?:number;name?:string;address?:string;mapsUrl?:string|null;phone?:string|null;telephoneUrl?:string|null;website?:string|null;businessStatus?:string;message?:string;refreshedAt?:string;attributions?:{provider?:string|null;uri?:string|null}[]};
export function mergeRefreshed(previous:Record<string,RefreshedVenue>,updates:Record<string,RefreshedVenue>,hoursOnly=false){
 const merged={...previous};
 for(const [id,value] of Object.entries(updates)){
  const old=previous[id];
  const credits=[...(old?.attributions??[]),...(value.attributions??[])].filter((credit,i,list)=>list.findIndex(c=>c.provider===credit.provider&&c.uri===credit.uri)===i);
  if(hoursOnly&&old?.name&&value.status==="refreshed"&&value.hoursEvidence){merged[id]={...old,hoursEvidence:value.hoursEvidence,attributions:credits};continue;}
  if(value.status==="refreshed"&&old?.hoursEvidence&&!value.hoursEvidence){merged[id]={...value,hoursEvidence:old.hoursEvidence,attributions:credits};continue;}
  merged[id]=value.status==="refreshed"||!old?.name?value:value.status==="already_attempted"?old:{...old,...value,status:"stale",message:value.message};
 }
 return merged;
}
