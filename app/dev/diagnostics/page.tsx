import {headers} from 'next/headers';
import {notFound} from 'next/navigation';
import {diagnosticBoundary} from '@/lib/development-access';
import {DevelopmentDiagnostics} from '@/components/development-diagnostics';
export const dynamic='force-dynamic';
export default async function DiagnosticsPage(){
 if(process.env.NODE_ENV!=='development')notFound();
 const incoming=await headers();
 const host=incoming.get('host')??'invalid';
 let boundary:Record<string,string>|null=null;
 try{boundary=diagnosticBoundary(new Request(`http://${host}/dev/diagnostics`,{headers:incoming}));}catch{notFound();}
 if(!boundary)notFound();
 let data:unknown;
 try{
  const response=await fetch(`${process.env.BACKEND_URL??'http://127.0.0.1:8000'}/api/development-diagnostics`,{headers:boundary,cache:'no-store',signal:AbortSignal.timeout(5000)});
  if(!response.ok)notFound();
  data=await response.json();
 }catch{notFound();}
 return <main className="shell reference-page"><a href="/">Return to planner</a><h1>Developer diagnostics</h1><p>Local sanitized counters and timing only. Loading this page does not contact Google.</p><DevelopmentDiagnostics initialData={data}/></main>;
}
