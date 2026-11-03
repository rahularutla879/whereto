import type {AdvancedData,Dwell} from './advanced-planning';
export type AdvancedPreferences={stops:{occurrence:number;requested:string;duration:Dwell|null;originalDuration:Dwell|null;override:boolean}[];budget:Dwell|null;budgetScope:'outing'|'travel';scopeOverride:boolean;departure:string|null;departureOverride:boolean;returnToOrigin:boolean;endpoint:string|null;deadlineSource?:string|null;choices:{occurrence:number;label:string;selectedId:string;choices:{placeId:string;name:string;address:string;attributions:{provider?:string|null;uri?:string|null}[]}[]}[]};
export type AdvancedDraft={stops:{occurrence:number;minutes:string;relation:Dwell['relation'];zeroCountedTime:boolean}[];budgetScope:'outing'|'travel';departure:string;choices:{occurrence:number;placeId:string}[]};
export function advancedDraft(data:AdvancedData):AdvancedDraft|null{
 const p=data.preferences;if(!p?.stops)return null;
 return {stops:p.stops.map(s=>({occurrence:s.occurrence,minutes:s.duration?String(s.duration.minutes):'',relation:s.duration?.relation??'exact',zeroCountedTime:s.duration?.minutes===0&&s.override})),budgetScope:p.budgetScope,departure:p.departure??'',choices:p.choices.map(c=>({occurrence:c.occurrence,placeId:c.selectedId}))};
}
export function advancedEdits(data:AdvancedData,draft:AdvancedDraft):Record<string,unknown>{
 const old=advancedDraft(data);if(!old)throw Error('Outing preferences are unavailable.');
 const dwell=draft.stops.filter(s=>{const before=old.stops.find(o=>o.occurrence===s.occurrence);return s.minutes!==''&&(s.minutes!==before?.minutes||s.relation!==before?.relation||s.zeroCountedTime!==before?.zeroCountedTime);}).map(s=>({occurrence:s.occurrence,minutes:Number(s.minutes),relation:s.relation,zeroCountedTime:s.zeroCountedTime}));
 const resetDwell=draft.stops.filter(s=>s.minutes===''&&old.stops.find(o=>o.occurrence===s.occurrence)?.minutes!=='').map(s=>s.occurrence);
 const choices=draft.choices.filter(c=>c.placeId&&old.choices.find(o=>o.occurrence===c.occurrence)?.placeId!==c.placeId);
 return {...(dwell.length?{dwell}:{}),...(resetDwell.length?{resetDwell}:{}),...(choices.length?{choices}:{}),...(draft.budgetScope!==old.budgetScope?{budgetScope:draft.budgetScope}:{}),...(draft.departure!==old.departure?(draft.departure?{departure:draft.departure}:{resetDeparture:true}):{})};
}
export function rememberAdvancedEdit(previous:Record<string,unknown>[],answer:Record<string,unknown>){
 if(!answer.edits)return [...previous.filter(a=>!Object.keys(answer).some(k=>k in a)),answer];
 const old=(previous.find(a=>a.edits)?.edits??{}) as Record<string,unknown>;
 const edit=answer.edits as Record<string,unknown>;
 const dwell=new Map(((old.dwell??[]) as {occurrence:number}[]).map(d=>[d.occurrence,d]));
 for(const n of (edit.resetDwell??[]) as number[])dwell.delete(n);
 for(const d of (edit.dwell??[]) as {occurrence:number}[])dwell.set(d.occurrence,d);
 const choices=new Map(((old.choices??[]) as {occurrence:number}[]).map(c=>[c.occurrence,c]));
 for(const c of (edit.choices??[]) as {occurrence:number}[])choices.set(c.occurrence,c);
 const merged:Record<string,unknown>={...old,...edit,dwell:[...dwell.values()],choices:[...choices.values()]};
 delete merged.resetDwell;
 if(edit.resetDeparture){delete merged.departure;delete merged.resetDeparture;}
 const rest={...answer};delete rest.edits;
 const base=previous.filter(a=>!a.edits);
 const carried=Object.keys(rest).length?[...base.filter(a=>!Object.keys(rest).some(k=>k in a)),rest]:base;
 return [...carried,{edits:merged}];
}
export const durationRelation=(value:string)=>({exact:'Exactly',maximum:'At most',minimum:'At least',under:'Under',approximate:'My estimate (approximate)'} as Record<string,string>)[value]??value;
