// Numeric development timing only; never forward arbitrary upstream headers.
export function timingHeaders(backend:string|null,total:number):Record<string,string>{
 if(process.env.NODE_ENV==="production"||!backend||!/^backend;dur=\d+(?:\.\d+)?$/.test(backend)||!Number.isFinite(total))return {};
 const elapsed=Number(backend.split('=')[1]);
 return {"Server-Timing":`${backend}, proxy;dur=${Math.max(0,total-elapsed).toFixed(3)}`};
}
