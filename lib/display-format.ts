import {activityLabel,type Activity} from './planner';
const destinations:Record<string,string>={'near me':'Near Me','current location':'Current Location','jersey city':'Jersey City','new york':'New York','new york city':'New York City','manhattan':'Manhattan','hyderabad':'Hyderabad','baltimore':'Baltimore','washington, dc':'Washington, DC','washington dc':'Washington, DC','san francisco':'San Francisco','los angeles':'Los Angeles','boston':'Boston','chicago':'Chicago','london':'London'};
// Only known destination spellings are normalized. Preserve arbitrary place/brand
// spelling, acronyms and punctuation; never title-case provider venue names.
export function destinationLabel(value:string){return destinations[value.trim().toLowerCase()]??value;}
export function transportLabel(value?:string|null){return ({walking:'Walking',driving:'Driving',cycling:'Cycling',transit:'Transit'} as Record<string,string>)[value??'driving']??value??'Driving';}
export function activityDisplay(value:string){
 const label=activityLabel(value as Activity);
 return label===label.toLowerCase()?label.charAt(0).toUpperCase()+label.slice(1):label;
}
export function outingDateLabel(value:string){return /^\d{4}-\d{2}-\d{2}$/.test(value)?new Date(value+'T12:00:00').toLocaleDateString('en-US',{month:'long',day:'numeric',year:'numeric'}):value;}
