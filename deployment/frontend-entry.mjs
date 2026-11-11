import process from 'node:process';
import { URL } from 'node:url';
// Container-only entry; no provider credentials, SDKs or deployment operations.
const reject=()=>{process.stderr.write('Frontend startup refused: invalid server configuration.\n');process.exit(78);};
const port=process.env.PORT??'8080';
if(!/^\d+$/.test(port)||Number(port)<1||Number(port)>65535)reject();
try{
  const url=new URL(process.env.BACKEND_URL??'');
  const local=['127.0.0.1','localhost','[::1]'].includes(url.hostname);
  if(!['https:','http:'].includes(url.protocol)||url.protocol==='http:'&&!local||url.username||url.password||url.search||url.hash||!['','/'].includes(url.pathname))reject();
}catch{reject();}
if(Object.keys(process.env).some(k=>/^NEXT_PUBLIC_.*(?:KEY|SECRET|TOKEN|PASSWORD|DATABASE|SUPABASE|DB_)/i.test(k))
  ||Object.entries(process.env).some(([k,v])=>k.startsWith('WHERETO_')&&k.endsWith('_DEV')&&v&&v!=='0'))reject();
process.env.NODE_ENV='production';process.env.HOSTNAME='0.0.0.0';process.env.PORT=port;
// Generated, traced Next server. No local source/test startup is selectable.
await import(new URL('../server.js',import.meta.url));
