import test from 'node:test';
import assert from 'node:assert/strict';
import { POST } from '../app/api/interpret/route';
import { providerProxy } from './provider-proxy';
import { persistenceProxy } from './persistence-proxy';
import { failureText } from './failure-diagnostics';

test('capacity and duplicate categories preserve status through every planning proxy', async () => {
  const original=globalThis.fetch;
  try {
    for(const [code,status] of [['service_busy',503],['request_burst_limited',429],['request_in_progress',409],['provider_quota_rejected',429]] as const){
      const message='Planning is temporarily busy. Your preferences are kept; please try again shortly.';
      globalThis.fetch=async()=>Response.json({code,message,correlationId:'0123456789abcdef'},{status});
      const request=()=>new Request('http://localhost/api/test',{method:'POST',body:'{}'});
      for(const response of [await POST(request()),await providerProxy('/api/plans/options',request()),await persistenceProxy('/api/plans/advanced',request())]){
        assert.equal(response.status,status);
        const data=await response.json();
        assert.equal(data.code,code);
        assert.equal(failureText(data,'fallback'),message);
        assert.equal(data.correlationId,'0123456789abcdef');
      }
    }
  } finally {globalThis.fetch=original;}
});

test('interpretation proxy propagates caller cancellation without a second upstream send', async () => {
  const original=globalThis.fetch;
  const controller=new AbortController();
  let calls=0;
  try {
    globalThis.fetch=async(_url,init)=>{
      calls++;
      controller.abort();
      assert.equal(init?.signal?.aborted,true);
      throw new DOMException('Aborted','AbortError');
    };
    const response=await POST(new Request('http://localhost/api/interpret',{method:'POST',body:'{}',signal:controller.signal}));
    assert.equal(response.status,503);
    assert.equal(calls,1);
    assert.doesNotMatch((await response.json()).message,/Qwen|Ollama|AbortError/);
  } finally {globalThis.fetch=original;}
});

test('classified continuation errors preserve recoverable and stopped search authority', async () => {
  const original=globalThis.fetch;
  const environment=process.env as Record<string,string|undefined>;
  const previous=environment.NODE_ENV;
  try {
    environment.NODE_ENV='production';
    for(const temporary of [true,false]){
      globalThis.fetch=async()=>Response.json({code:temporary?'provider_local_rate_limit':'provider_quota_rejected',
        message:'Search capacity is temporarily unavailable.',diagnostics:{failureBoundary:temporary?'local_minute':'provider_or_unknown'},
        continuation:{canExpand:temporary,canDiscover:temporary,privateField:'do not forward'}},{status:429});
      const response=await providerProxy('/api/plans/options',new Request('http://localhost/api/plans/options',{method:'POST',body:'{}'}));
      assert.equal(response.status,429);
      const data=await response.json();
      assert.equal(data.resumable,temporary);
      assert.deepEqual(data.continuation,{canExpand:temporary,canDiscover:temporary});
      assert.equal(data.diagnostics,undefined);
    }
  } finally {
    globalThis.fetch=original;
    if(previous===undefined)delete environment.NODE_ENV;else environment.NODE_ENV=previous;
  }
});
