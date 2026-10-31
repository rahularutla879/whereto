"use client";
import {useState} from "react";
export function DevelopmentDiagnostics(){
 const [data,setData]=useState<unknown>(null);
 const [message,setMessage]=useState("");
 if(process.env.NODE_ENV!=="development")return null;
 return <details className="development-panel"><summary>Local development tools</summary><button type="button" className="secondary-button" onClick={async()=>{try{const response=await fetch("/api/development-diagnostics",{cache:"no-store"});if(!response.ok)throw new Error();setData(await response.json());setMessage("");}catch{setMessage("Diagnostics require the authorized local development profile.");}}}>Load diagnostics</button>{message&&<p role="status">{message}</p>}{data!==null&&<pre aria-label="Sanitized development diagnostics">{JSON.stringify(data,null,2)}</pre>}</details>;
}
