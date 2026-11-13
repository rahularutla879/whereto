/* global Response */
import process from 'node:process';import {Buffer} from 'node:buffer';
// Local-only BUILD cohort. No signer or privileged-controller credential exists here.
import fs from 'node:fs';import https from 'node:https';import {createLocalJWKSet} from 'jose';
import {composeIdentityPort} from './identity-port-v2.mjs';
if(process.env.K_SERVICE||process.env.VERCEL||process.env.RENDER)throw Error('Local identity cohort cannot run hosted');
const endpoint='https://identity.task52.invalid:8443';
async function get(path){return new Promise((resolve,reject)=>{const r=https.get(endpoint+path,{ca:fs.readFileSync('/run/secrets/local-fixture-ca.crt'),rejectUnauthorized:true,timeout:2000},response=>{let n=0;const chunks=[];response.on('data',b=>{n+=b.length;if(n>100000)r.destroy(Error('Bound'));else chunks.push(b);});response.on('end',()=>response.statusCode===200?resolve(new Response(Buffer.concat(chunks),{headers:{'Metadata-Flavor':'Google'}})):reject(Error('Refused')));});r.on('error',reject);r.on('timeout',()=>r.destroy(Error('Timeout')));});}
export function createGoogleIdentityPort(c){let port;return Object.freeze({async initialize(){const workload=await(await get('/workload')).json(),iap=await(await get('/iap')).json();port=composeIdentityPort(c,{fixture:true,workload:createLocalJWKSet(workload),iap:createLocalJWKSet(iap),metadata:()=>get('/metadata?audience='+encodeURIComponent(c.backendAudience))});await port.initialize();},verifyAndSeal(input){if(!port)throw Error('Not ready');return port.verifyAndSeal(input);}});}
