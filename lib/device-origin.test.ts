import test from 'node:test';import assert from 'node:assert/strict';
import {requestDeviceOrigin,requireDeviceOrigin,type DeviceOrigin} from './device-origin';
import {PrivateOrdinaryClient} from './private-ordinary-client';
function browser(work:(ok:PositionCallback,fail:PositionErrorCallback|null,options?:PositionOptions)=>void){
 const prior=Object.getOwnPropertyDescriptor(globalThis,'navigator');Object.defineProperty(globalThis,'navigator',{configurable:true,value:{geolocation:{getCurrentPosition:work}}});
 return ()=>{if(prior)Object.defineProperty(globalThis,'navigator',prior);else Reflect.deleteProperty(globalThis,'navigator');};
}
function position(){return {coords:{latitude:39.29,longitude:-76.61,accuracy:20},timestamp:Date.now()} as GeolocationPosition;}
test('browser-only location is explicit, fresh and cannot be reconstructed from manual JSON',async()=>{
 let calls=0;const reset=browser((ok,_,options)=>{calls++;assert.equal(options?.maximumAge,0);assert.equal(options?.timeout,10000);ok(position());});
 try{assert.equal(calls,0);const value=await requestDeviceOrigin();assert.equal(calls,1);assert.equal(requireDeviceOrigin(value),value);assert.throws(()=>requireDeviceOrigin(JSON.parse(JSON.stringify(value))));}finally{reset();}
});
test('denied, unavailable, inaccurate and stale browser observations never invent an origin',async()=>{
 let reset=browser((_,fail)=>fail?.({code:1} as GeolocationPositionError));try{await assert.rejects(requestDeviceOrigin(),/permission was denied/);}finally{reset();}
 for(const p of [{...position(),timestamp:Date.now()-61000},{...position(),coords:{...position().coords,accuracy:6000}},{...position(),coords:{...position().coords,latitude:NaN}}]){reset=browser(ok=>ok(p as GeolocationPosition));try{await assert.rejects(requestDeviceOrigin(),/unavailable, inaccurate or stale/);}finally{reset();}}
 assert.throws(()=>requireDeviceOrigin({latitude:0,longitude:0,accuracy:1,observedAt:Date.now()} as DeviceOrigin));
});
test('real client never labels manual coordinates as device; observed origin is the sole generation body',async()=>{
 const calls:{url:string;body:Record<string,unknown>}[]=[];const c=new PrivateOrdinaryClient(async(url,init)=>{calls.push({url:String(url),body:JSON.parse(String(init?.body))});return Response.json(calls.length===1?{privateOuting:{version:'52-private-ordinary-outing-v1',handle:'A'.repeat(43),revision:1,expiresMs:Date.now()+60000},questions:[],issues:[],request:{activities:['coffee'],location:'Baltimore',date:'2099-11-07',transport:'driving',startTime:600,endTime:1440},interpretation:{}}:{provisionalPlans:[],message:'No results',notes:[],dataMode:'real'});},'real');
 await c.interpret('Coffee');await assert.rejects(c.generate(39,-76),/browser device location/);assert.equal(calls.length,1);
 const reset=browser(ok=>ok(position()));try{await c.generateDevice(await requestDeviceOrigin());}finally{reset();}
 assert.equal(calls.length,2);assert.deepEqual(calls[1].body.startingLocation,{point:{id:'device-origin',coordinates:{latitude:39.29,longitude:-76.61}},explicitly_authorized:true,source:'device'});assert.equal(calls[1].body.searchRadius,undefined);
});
