import test from "node:test";
import assert from "node:assert/strict";
import {createElement} from "react";
import {renderToStaticMarkup} from "react-dom/server";
import {AlternativeActions} from "../components/alternative-actions";
import {explorationStage} from "../components/exploration-notice";
test("alternative actions have distinct simple descriptions and accessible busy status",()=>{
  const html=renderToStaticMarkup(createElement(AlternativeActions,{real:true,canCombine:true,canExplore:true,busy:false,disabled:false,notice:"",onAction(){throw Error("Unexpected request");},onAdjust(){}}));
  assert.match(html,/Show different options/);assert.match(html,/Explore farther/);
  assert.match(html,/Try different combinations from places already found/);
  assert.match(html,/Discover new places in a wider area/);
  assert.doesNotMatch(html,/provider pages|candidate pool|shared budget|Search for more venues/i);
  const busy=renderToStaticMarkup(createElement(AlternativeActions,{real:true,canCombine:true,canExplore:true,busy:true,disabled:false,notice:"Exploring areas…",onAction(){},onAdjust(){}}));
  assert.match(busy,/aria-busy="true"/);assert.equal((busy.match(/disabled=""/g)||[]).length,3);
  assert.match(busy,/role="status"/);
  assert.match(explorationStage(true),/Exploring areas/);assert.match(explorationStage(false),/Checking routes/);
});
test("mock alternatives do not offer provider discovery",()=>{
  const html=renderToStaticMarkup(createElement(AlternativeActions,{real:false,canCombine:true,canExplore:false,busy:false,disabled:false,notice:"",onAction(){},onAdjust(){}}));
  assert.match(html,/Show different options/);assert.doesNotMatch(html,/Explore farther/);
});
test("only unsent contact lookups can be deliberately reopened after local recovery",async()=>{
  const {VenueDetailsSession,ContactLookupError}=await import("./venue-details");
  const session=new VenueDetailsSession();let calls=0;
  const send:typeof fetch=async()=>{calls++;return calls===1?Response.json({message:"Local accounting access denied",diagnostics:{contactRequestAdmitted:false}},{status:422}):Response.json({placeId:"Synthetic_A",phone:null,website:"https://example.com",attributions:[]});};
  await assert.rejects(session.get("token","Synthetic_A",send),e=>e instanceof ContactLookupError&&e.notAdmitted);
  await assert.rejects(session.get("token","Synthetic_A",send));assert.equal(calls,1);
  session.retryUnsent("token","Synthetic_A");
  assert.equal((await session.get("token","Synthetic_A",send)).website,"https://example.com/");
  assert.equal(calls,2);
  const provider=new VenueDetailsSession();
  await assert.rejects(provider.get("token","Synthetic_B",async()=>Response.json({message:"Place Details quota exhausted",diagnostics:{contactRequestAdmitted:true}},{status:422})),e=>e instanceof ContactLookupError&&!e.notAdmitted);
});
test("contact proxy preserves only the safe pre-admission decision for explicit recovery",async()=>{
  const {providerProxy}=await import("./provider-proxy");
  const original=globalThis.fetch;
  try{
    globalThis.fetch=async()=>Response.json({message:"Local accounting access denied",diagnostics:{contactRequestAdmitted:false,secret:"MUST_NOT_FORWARD"}},{status:422});
    const response=await providerProxy("/api/venues/details",new Request("http://localhost/api/venues/details",{method:"POST",body:JSON.stringify({token:"synthetic",placeId:"Synthetic_A"})}));
    const data=await response.json();
    assert.deepEqual(data.diagnostics,{contactRequestAdmitted:false});
    assert.doesNotMatch(JSON.stringify(data),/MUST_NOT_FORWARD/);
  }finally{globalThis.fetch=original;}
});
