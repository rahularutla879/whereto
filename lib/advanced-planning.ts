import type {Plan,PlannerResult,Activity} from './planner';
import type {LocationContext} from './planning-client';
import type {HoursEvidence} from './venue-hours';
export type Dwell={minutes:number;relation:'exact'|'minimum'|'maximum'|'under'|'approximate';source:string};
export type AdvancedStop={occurrence:number;requested:string;requirement:'required'|'optional';placeId:string;name:string;address:string|null;mapsUrl:string;duration:Dwell|null;arrival:string|null;departure:string|null;hoursState:string;hours:HoursEvidence;rating:number|null;ratingCount:number|null;credits:{provider?:string|null;uri?:string|null}[]};
export type AdvancedOption={id:string;state:'feasible'|'unverified';routeState:string;stops:AdvancedStop[];ending:'last_activity'|'origin'|'named_destination';endpoint:{placeId:string;name:string;mapsUrl:string;credits:AdvancedStop['credits']}|null;legs:{role:string;fromOccurrence:number|null;toOccurrence:number|null;seconds:number|null;meters:number|null;status:string;mode:string;mapsUrl?:string|null}[];knownTravelSeconds:number;elapsedLowerSeconds:number;elapsedUpperSeconds:number|null;upperExclusive:boolean;totalConstraint:Dwell|null;deadlineSource:string|null;durationState:string;deadlineState:string;reasons:string[];omitted:{occurrence:number;requested:string;reason:string}[]};
export type AdvancedQuestion={field:'place'|'date'|'destination'|'origin'|'dwell'|'departure';question:string;occurrence?:number;choices?:{placeId:string;name:string;address:string;attributions:AdvancedStop['credits']}[]};
export type AdvancedData={kind:'advanced';token:string;status:string;message:string;date:string|null;destination:string|null;transport:'driving'|'walking';questions:AdvancedQuestion[];options:AdvancedOption[];saveReceipt?:string;saveAccessToken?:string;code?:string;bounded:true};
export type AdvancedState={continuation?:import('./planning-client').PendingOuting;data:AdvancedData;configuration:Pick<LocationContext,'startingLocation'|'firstTravel'|'betweenTravel'>};
export function adaptAdvanced(raw:AdvancedData,configuration:AdvancedState['configuration']):PlannerResult{
 if(raw?.kind!=='advanced'||!(/^[A-Za-z0-9_-]{43}$/).test(raw.token)||!Array.isArray(raw.options)||raw.options.length>3||!Array.isArray(raw.questions)||typeof raw.message!=='string'||!['driving','walking'].includes(raw.transport))throw Error('Advanced response could not be verified.');
 const themes=['lavender','peach','mint'] as const;
 const plans:Plan[]=raw.options.map((option,i)=>{
  if(!['feasible','unverified'].includes(option.state)||!Array.isArray(option.stops)||!option.stops.length||option.stops.length>4||!Array.isArray(option.legs)||!Array.isArray(option.reasons)||option.stops.some(s=>typeof s.name!=='string'||typeof s.placeId!=='string'||!Number.isInteger(s.occurrence))||!raw.date)throw Error('Incomplete advanced itinerary.');
  const venues=option.stops.map(s=>({id:s.placeId,providerPlaceId:s.placeId,name:s.name,activity:'custom:'+s.requested.toLowerCase().slice(0,100) as Activity,kind:'venue' as const,address:s.address,mapsUrl:s.mapsUrl,price:null,duration:null,capacity:null,neighborhood:null,zone:0,experience:0,dataQuality:{identity:'verified'},hoursEvidence:s.hours}));
  return {advanced:option,id:option.id,title:option.stops.map(s=>s.name).join(' → '),description:raw.message,theme:themes[i],label:`OPTION ${i+1}`,transport:raw.transport,dataMode:'real',location:raw.destination??'Named destinations',venues,stops:venues.map(venue=>({venue,start:null,end:null})),price:null,groupCost:null,travel:option.knownTravelSeconds/60,duration:option.elapsedUpperSeconds===option.elapsedLowerSeconds?option.elapsedLowerSeconds/60:null,date:raw.date,feasibility:option.state==='feasible'?'confirmed':'provisional',issues:option.reasons,prices:venues.map(()=>({amount:null,status:'unknown'})),legs:option.legs.filter(l=>l.role==='inter_activity').map(l=>({minutes:l.seconds===null?null:l.seconds/60,status:l.status}))};
 });
 if(new Set(plans.map(p=>p.id)).size!==plans.length)throw Error('Duplicate advanced options.');
 return {advanced:{data:raw,configuration},dataMode:'real',plans,message:raw.message,location:raw.destination??'',activities:plans[0]?.venues.map(v=>v.activity)??[],notes:[],saveReceipt:raw.saveReceipt??undefined,saveAccessToken:raw.saveAccessToken??undefined};
}
export async function continueAdvanced(state:AdvancedState,answer:Record<string,unknown>={},signal?:AbortSignal,send:typeof fetch=fetch){
 const response=await send('/api/plans/advanced',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token:state.data.token,...state.configuration,...answer}),cache:'no-store',signal});
 const data=await response.json();
 if(!response.ok)throw Error(typeof data.message==='string'?data.message:'Advanced planning unavailable. Your request is kept.');
 const next=adaptAdvanced(data,state.configuration);if(next.advanced)next.advanced.continuation=state.continuation;return next;
}
