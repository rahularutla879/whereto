import {failureText} from "./failure-diagnostics";
import type {RefreshedVenue} from "./saved-plan-refresh";
// One explicit action, one UUID, no retries. Provider content stays in memory.
export async function loadSavedDetails(accessToken:string,candidateId:string,includeContacts=false){
 const response=await fetch("/api/plans/refresh",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({accessToken,candidateId,includeContacts,refreshId:crypto.randomUUID()}),cache:"no-store"});
 const data=await response.json();
 if(!response.ok)throw new Error(failureText(data,data.message??"Venue details unavailable. Your saved plan is kept."));
 if(data.candidateId!==candidateId||!data.venues||typeof data.venues!=="object"||Array.isArray(data.venues))throw new Error("Venue response could not be verified.");
 return data.venues as Record<string,RefreshedVenue>;
}
export function detailsFeedback(venues:Record<string,RefreshedVenue>){
 const values=Object.values(venues),loaded=values.filter(v=>v.status==="refreshed").length;
 const messages=[...new Set(values.filter(v=>v.status!=="refreshed").map(v=>v.message?`${v.message}${v.retryAfterSeconds?` Try again in about ${v.retryAfterSeconds} seconds.`:""}`:undefined).filter(Boolean))];
 return `${loaded} ${loaded===1?"stop":"stops"} loaded.${messages.length?" "+messages.join(" "):" Current venue information; original routes are not retained."}`;
}
