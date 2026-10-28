import test from "node:test";
import assert from "node:assert/strict";
import { providerProxy } from "./provider-proxy";
import { POST } from "../app/api/plans/generate/route";

test("client cancellation propagates to both planning proxies without retries",async()=>{
  const original=globalThis.fetch;
  try {
    for (const action of [
      (r:Request)=>POST(r),
      (r:Request)=>providerProxy("/api/plans/options",r),
    ]) {
      const controller=new AbortController();
      let calls=0;let signal:AbortSignal|null|undefined;
      globalThis.fetch=async(_url,init)=>{
        calls++;signal=init?.signal;
        controller.abort();
        signal?.throwIfAborted();
        throw Error("Cancelled");
      };
      await action(new Request("http://localhost/api/plans/options",{method:"POST",body:JSON.stringify({token:"invented"}),signal:controller.signal}));
      assert.equal(calls,1);assert.equal(signal?.aborted,true);
    }
  } finally {globalThis.fetch=original;}
});
test("only confirmed local-minute admission errors remain resumable",async()=>{
  const original=globalThis.fetch;
  try{
    for(const [boundary,resumable] of [["local_minute",true],["provider_or_unknown",false],["local_spending_guard",false]] as const){
      globalThis.fetch=async()=>Response.json({message:"Safe fixture explanation",diagnostics:{failureBoundary:boundary}},{status:422});
      const response=await providerProxy("/api/plans/options",new Request("http://localhost/api/plans/options",{method:"POST",body:"{}"}));
      assert.equal((await response.json()).resumable,resumable);
    }
  }finally{globalThis.fetch=original;}
});
