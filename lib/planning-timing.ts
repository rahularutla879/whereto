// Development measurements contain fixed stage labels and durations only.
let started=0;
let measurements:Record<string,number>={};
export function beginPlanningTiming(){if(process.env.NODE_ENV==='development'){started=performance.now();measurements={};}}
export function recordPlanningTiming(name:'loadingFeedbackMs'|'browserTotalMs'|'originPreparationMs'|'interpretationHttpMs'|'planningHttpMs',ms:number){
 if(process.env.NODE_ENV==='development'&&started&&Number.isFinite(ms)&&ms>=0)measurements[name]=Math.round(ms*1000)/1000;
}
export function planningElapsed(){return started?performance.now()-started:0;}
export function planningTiming(){return {...measurements};}
export async function measurePlanning<T>(name:'originPreparationMs'|'interpretationHttpMs'|'planningHttpMs',operation:()=>Promise<T>):Promise<T>{
 const start=performance.now();try{return await operation();}finally{recordPlanningTiming(name,performance.now()-start);}
}
