"use client";
import {useState} from "react";
export function DevelopmentDiagnostics({initialData=null}:{initialData?:unknown}){
 const [data,setData]=useState<unknown>(initialData);
 const [message,setMessage]=useState("");
 if(process.env.NODE_ENV!=="development")return null;
 return <section className="development-panel" aria-label="Developer diagnostics"><button type="button" className="secondary-button" onClick={async()=>{try{const response=await fetch("/api/development-diagnostics",{cache:"no-store"});if(!response.ok)throw new Error();setData(await response.json());setMessage("");}catch{setMessage("Diagnostics require the authorized local development profile.");}}}>Reload diagnostics</button>{message&&<p role="status">{message}</p>}{data!==null&&<pre aria-label="Sanitized development diagnostics">{JSON.stringify(data,null,2)}</pre>}</section>;
}
