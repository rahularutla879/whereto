// Additive ownership extension, emitted only by the selected private profile.
export type PrivateOuting={version:'52-private-ordinary-outing-v1';handle:string;revision:number;expiresMs:number};
export function privateOuting(value:unknown):PrivateOuting|undefined {
 if(value===undefined)return;
 if(!value||typeof value!=='object')throw Error('Invalid private outing');
 const v=value as PrivateOuting;
 if(Object.keys(v).sort().join()!=='expiresMs,handle,revision,version'||v.version!=='52-private-ordinary-outing-v1'||!/^[A-Za-z0-9_-]{43}$/.test(v.handle)||!Number.isSafeInteger(v.revision)||v.revision<1||!Number.isSafeInteger(v.expiresMs)||v.expiresMs<=Date.now())throw Error('Invalid private outing');
 return v;
}
