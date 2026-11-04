/** Presentation only: never use formatted/rounded values to evaluate constraints. */
export function formatSeconds(value:number|null|undefined, precision:'nearest'|'lower'|'upper'='nearest'):string {
 if(value==null||!Number.isFinite(value)||value<0)return 'Unknown';
 const total=precision==='lower'?Math.floor(value):precision==='upper'?Math.ceil(value):Math.round(value);
 const hours=Math.floor(total/3600), minutes=Math.floor(total%3600/60), seconds=total%60;
 return [hours?`${hours} hr`:'',minutes?`${minutes} min`:'',seconds?`${seconds} sec`:''].filter(Boolean).join(' ')||'0 sec';
}
export function formatDuration(minutes:number|null|undefined):string {
 return formatSeconds(minutes==null?minutes:minutes*60);
}
