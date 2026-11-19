/* global Response, URL, console */
// Local signed-identity fixture only. No signer or provider credential enters Next.
import fs from 'node:fs';import process from 'node:process';import {createLocalJWKSet} from 'jose';
import {composeIdentityPort} from './identity-port-v2.mjs';
if(process.env.K_SERVICE||process.env.VERCEL||process.env.RENDER)throw Error('Local fixture cannot run hosted');
export function createGoogleIdentityPort(c){let port;return Object.freeze({async initialize(){const d=JSON.parse(fs.readFileSync(new URL('../secrets/identity.json',import.meta.url),'utf8'));if(d.audience!==c.backendAudience)throw Error('Fixture audience');port=composeIdentityPort(c,{fixture:true,workload:createLocalJWKSet(d.workload),iap:createLocalJWKSet(d.iap),metadata:async()=>new Response(d.token,{headers:{'Metadata-Flavor':'Google'}})});await port.initialize();},verifyAndSeal(v){if(!port)throw Error('Not initialized');return port.verifyAndSeal(v).catch(e=>{console.error(JSON.stringify({fixtureStage:"identity",error:e.code??e.name}));throw e;});}});}
