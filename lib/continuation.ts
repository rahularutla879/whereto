import type {PlannerResult} from './planner';
// Compare wording variants before rendering; preserve distinct actionable errors.
export function planningMessage(primary:string,errors:{message:string}[]){
 const seen=new Set<string>();
 return [primary,...errors.map(e=>e.message)].filter(message=>{
  const key=message.replace(/[’']/g,"'").replace(/\bwe've\b/gi,'we have').replaceAll('openingHours','opening hours').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim();
  if(!key||seen.has(key))return false;seen.add(key);return true;
 }).join(' ');
}
export function restoreContinuation(page:PlannerResult,latest:PlannerResult):PlannerResult{
 return {...page,canExpand:latest.canExpand,canDiscover:latest.canDiscover,canShowBeyond:latest.canShowBeyond,continuationStatus:latest.continuationStatus};
}
// Empty initial results already explain themselves in PlanningFeedback. Keep
// continuation feedback here only for an explicit subsequent action.
export function continuationNotice(result:PlannerResult,notice=''){
 if(notice)return notice;
 if(!result.plans.length)return '';
 if(result.continuationStatus?.kind==='checked_pool_exhausted')return 'No more matching combinations found among the places checked so far.'+(result.canDiscover?' You can look for more nearby places.':' Other venues may exist.');
 return result.continuationStatus?.message??(!result.canExpand&&!result.canDiscover?"No more matching combinations found among the places checked so far. Other venues may exist.":'');
}
