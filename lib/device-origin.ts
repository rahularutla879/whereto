// Browser-observed provenance, not hardware attestation or provider evidence.
export type DeviceOrigin=Readonly<{latitude:number;longitude:number;accuracy:number;observedAt:number}>;
const observed=new WeakSet<object>();
export function requireDeviceOrigin(value:DeviceOrigin){
 if(!observed.has(value)||!Number.isFinite(value.latitude)||Math.abs(value.latitude)>90||!Number.isFinite(value.longitude)||Math.abs(value.longitude)>180||!Number.isFinite(value.accuracy)||value.accuracy<0||value.accuracy>5000||!Number.isFinite(value.observedAt)||value.observedAt>Date.now()+5000||Date.now()-value.observedAt>60000)throw Error('Browser location is unavailable, inaccurate or stale. Choose Use my location again; no planning request was sent.');
 return value;
}
export function requestDeviceOrigin():Promise<DeviceOrigin>{
 return new Promise((resolve,reject)=>{
  if(typeof navigator==='undefined'||!navigator.geolocation){reject(Error('Browser location is unavailable. This private profile cannot plan without a confirmed device origin.'));return;}
  navigator.geolocation.getCurrentPosition(position=>{
   const value=Object.freeze({latitude:position.coords.latitude,longitude:position.coords.longitude,accuracy:position.coords.accuracy,observedAt:position.timestamp});observed.add(value);
   try{resolve(requireDeviceOrigin(value));}catch(error){reject(error);}
  },()=>reject(Error('Location permission was denied or location could not be obtained. No planning request was sent. Allow location and choose Use my location again.')),{enableHighAccuracy:false,maximumAge:0,timeout:10000});
 });
}
